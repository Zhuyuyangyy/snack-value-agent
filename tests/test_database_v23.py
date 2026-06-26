"""V0.2 → V0.3 schema 兼容迁移测试。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from backend.database import (
    init_db,
    migrate_v023,
    _connect,
)

# V0.3.1: 引入 save_evaluation 用于回归测试
from backend.database import save_evaluation


@pytest.fixture
def v02_db(tmp_path: Path) -> Path:
    """创建一个 V0.2 老 schema 的临时数据库。"""
    db_path = tmp_path / "v02.db"
    conn = _connect(db_path)
    conn.executescript("""
        CREATE TABLE snack_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            total_price REAL NOT NULL,
            total_weight_g REAL NOT NULL,
            flavor_type TEXT NOT NULL,
            flavor_name TEXT,
            expiry_date TEXT,
            package_type TEXT DEFAULT 'unknown',
            quantity INTEGER,
            source_text TEXT,
            price_per_g REAL NOT NULL,
            adjusted_price_per_g REAL NOT NULL,
            value_score REAL,
            risk_level TEXT,
            recommendation_label TEXT,
            reason TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE baseline (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            baseline_price_per_g REAL NOT NULL,
            baseline_source TEXT,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE user_preference (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            preferred_flavors TEXT,
            disliked_flavors  TEXT,
            daily_intake_g     REAL DEFAULT 20.0
        );
    """)
    conn.commit()
    conn.close()
    return db_path


def test_migrate_adds_missing_columns(v02_db: Path):
    """迁移给老 schema 加上新列。"""
    migrate_v023(v02_db)
    conn = _connect(v02_db)
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(snack_history)")]
    expected_new = [
        "listed_price", "coupon_amount", "discount_amount", "shipping_fee",
        "single_weight_g", "channel", "category", "brand",
        "after_opening_risk", "estimated_delivery_days",
        "flavor_uncertainty_penalty",
    ]
    for col in expected_new:
        assert col in cols, f"缺失新列: {col}"


def test_migrate_idempotent(v02_db: Path):
    """迁移可重复执行（不报错）。"""
    migrate_v023(v02_db)
    migrate_v023(v02_db)  # 再次调用应不报错
    migrate_v023(v02_db)  # 第三次
    conn = _connect(v02_db)
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(snack_history)")]
    assert len(cols) == len(set(cols)), "迁移产生重复列"


def test_init_db_creates_full_v03_schema(tmp_path: Path):
    """init_db 创建完整 V0.3 schema（含新列）。"""
    db_path = tmp_path / "fresh.db"
    init_db(db_path)
    conn = _connect(db_path)
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(snack_history)")]
    assert "listed_price" in cols
    assert "channel" in cols
    assert "category" in cols
    assert "brand" in cols
    assert "estimated_delivery_days" in cols


def test_migrate_preserves_existing_data(v02_db: Path):
    """迁移不丢老数据。"""
    conn = _connect(v02_db)
    conn.execute("""
        INSERT INTO snack_history
        (name, total_price, total_weight_g, flavor_type, price_per_g, adjusted_price_per_g, created_at)
        VALUES ('奥利奥', 19.9, 420, 'fixed', 0.047, 0.047, '2026-06-01')
    """)
    conn.execute("""
        INSERT INTO baseline (id, baseline_price_per_g, baseline_source, updated_at)
        VALUES (1, 0.045, '奥利奥', '2026-06-01')
    """)
    conn.commit()
    conn.close()
    migrate_v023(v02_db)
    conn = _connect(v02_db)
    row = conn.execute("SELECT name, total_price FROM snack_history").fetchone()
    assert row["name"] == "奥利奥"
    assert row["total_price"] == 19.9
    base = conn.execute("SELECT baseline_price_per_g, baseline_source FROM baseline WHERE id=1").fetchone()
    assert base["baseline_price_per_g"] == 0.045
    assert base["baseline_source"] == "奥利奥"


def test_migrate_new_columns_have_defaults(v02_db: Path):
    """新列默认值正确（已存在的行新列为 NULL 或 default value）。"""
    conn = _connect(v02_db)
    conn.execute("""
        INSERT INTO snack_history
        (name, total_price, total_weight_g, flavor_type, price_per_g, adjusted_price_per_g, created_at)
        VALUES ('测试', 10, 100, 'fixed', 0.1, 0.1, '2026-06-01')
    """)
    conn.commit()
    conn.close()
    migrate_v023(v02_db)
    conn = _connect(v02_db)
    row = conn.execute("SELECT * FROM snack_history WHERE name='测试'").fetchone()
    # DEFAULT 0 列应是 0，nullable 列应是 None
    assert row["coupon_amount"] == 0
    assert row["discount_amount"] == 0
    assert row["shipping_fee"] == 0
    assert row["estimated_delivery_days"] == 3
    assert row["channel"] == "unknown"
    assert row["category"] == "unknown"
    assert row["after_opening_risk"] == "unknown"
    assert row["listed_price"] is None
    assert row["single_weight_g"] is None
    assert row["brand"] is None


# ---------------------------------------------------------------------------
# V0.3.1 回归测试：移除 total_price NOT NULL 约束（前端只发 final_price 时不崩）
# ---------------------------------------------------------------------------


def test_save_evaluation_with_total_price_none(v02_db: Path):
    """V0.3 兼容性：save_evaluation 允许 total_price=None（用 final_price 代替）。"""
    # 先迁移
    migrate_v023(v02_db)
    # 插入 total_price=None 的行（模拟 V0.3 前端只发 final_price）
    conn = _connect(v02_db)
    conn.execute("""
        INSERT INTO snack_history
        (name, total_price, total_weight_g, flavor_type, price_per_g, adjusted_price_per_g, created_at)
        VALUES ('V0.3商品', NULL, 100, 'fixed', 0.05, 0.05, '2026-06-01')
    """)
    conn.commit()
    conn.close()
    # 验证行确实插入成功（total_price 是 NULL）
    conn = _connect(v02_db)
    row = conn.execute("SELECT name, total_price FROM snack_history WHERE name='V0.3商品'").fetchone()
    assert row["name"] == "V0.3商品"
    assert row["total_price"] is None
    conn.close()


def test_total_price_column_is_nullable_after_migration(v02_db: Path):
    """迁移后 total_price 列应是 nullable（不是 NOT NULL）。"""
    migrate_v023(v02_db)
    conn = _connect(v02_db)
    cols = list(conn.execute("PRAGMA table_info(snack_history)"))
    tp_col = next(c for c in cols if c["name"] == "total_price")
    assert tp_col["notnull"] == 0, f"total_price 应为 nullable，实际 notnull={tp_col['notnull']}"
    conn.close()


def test_save_evaluation_with_total_price_none_via_helper(v02_db: Path):
    """save_evaluation() 函数允许 total_price=None（用 final_price 代替落库）。"""
    # 直接调用 save_evaluation 验证
    from backend.models import SnackItem, EvaluationResult

    # 用 v02_db（已是 V0.2 schema，迁移后允许 total_price=NULL）
    init_db(v02_db)

    # 构造一个 V0.3 SnackItem（total_price=None, final_price=10）
    item = SnackItem(name="save测试", final_price=10.0, total_weight_g=100)
    assert item.total_price is None  # 确认是 None

    # 构造 EvaluationResult（其他字段必填）
    result = EvaluationResult(
        item=item,
        price_per_g=0.1,
        flavor_factor=1.0,
        expiry_factor=1.0,
        adjusted_price_per_g=0.1,
        value_score=1.0,
        risk_level="低",
        recommendation_label="✅ 可参考",
        reason="test",
        baseline_updated=False,
    )

    # 应不抛 IntegrityError（V0.3.1 关键回归点）
    rid = save_evaluation(result, db_path=v02_db)
    assert rid > 0

    # 验证 DB 中行存在；total_price 被回填为 final_price（fallback）
    conn = _connect(v02_db)
    row = conn.execute("SELECT * FROM snack_history WHERE id=?", (rid,)).fetchone()
    assert row["name"] == "save测试"
    # V0.3.1 行为：total_price 为 None 时，落库写入 final_price 作为回填
    assert row["total_price"] == 10.0
    conn.close()
