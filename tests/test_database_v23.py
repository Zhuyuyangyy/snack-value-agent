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
