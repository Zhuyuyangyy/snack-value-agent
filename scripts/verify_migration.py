"""V0.2 → V0.3 数据迁移验证脚本。

用法：
    /d/python实验/python.exe scripts/verify_migration.py

验证：
    - 老 DB 应用 migrate_v023 后，所有新列存在
    - 老数据完整保留
    - 新列默认值正确
"""
import sys
import io
import shutil
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows (avoid GBK codec errors for emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根到 path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import _connect, init_db, migrate_v023


def main():
    print("=== V0.2 → V0.3 数据迁移验证 ===\n")

    with tempfile.TemporaryDirectory() as tmp:
        v02_db = Path(tmp) / "v02_test.db"

        # 1. 创建 V0.2 schema
        conn = _connect(v02_db)
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
        """)
        # 插入测试数据
        conn.execute("""
            INSERT INTO snack_history
            (name, total_price, total_weight_g, flavor_type, flavor_name, price_per_g, adjusted_price_per_g, created_at)
            VALUES ('测试老数据', 19.9, 420, 'fixed', '原味', 0.047, 0.047, '2026-01-01')
        """)
        conn.commit()
        conn.close()
        print("✅ V0.2 schema 创建 + 测试数据插入")

        # 2. 运行迁移
        migrate_v023(v02_db)
        print("✅ migrate_v023 执行")

        # 3. 验证新列
        conn = _connect(v02_db)
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(snack_history)")]
        expected_new = ["listed_price", "coupon_amount", "shipping_fee", "channel",
                        "category", "brand", "estimated_delivery_days"]
        for col in expected_new:
            assert col in cols, f"缺失新列: {col}"
        print(f"✅ 全部 {len(expected_new)} 新列已添加")

        # 4. 验证老数据保留
        row = conn.execute("SELECT * FROM snack_history WHERE name='测试老数据'").fetchone()
        assert row is not None, "老数据丢失"
        assert row["total_price"] == 19.9, "老数据值错误"
        assert row["flavor_name"] == "原味", "老数据口味丢失"
        # 新列默认值
        assert row["coupon_amount"] == 0
        assert row["shipping_fee"] == 0
        assert row["channel"] == "unknown"
        assert row["estimated_delivery_days"] == 3
        print("✅ 老数据保留 + 新列默认值正确")

        # 5. 验证幂等性
        migrate_v023(v02_db)
        migrate_v023(v02_db)
        cols2 = [row["name"] for row in conn.execute("PRAGMA table_info(snack_history)")]
        assert len(cols2) == len(set(cols2)), "迁移产生重复列"
        print("✅ 迁移幂等（重复执行无副作用）")
        conn.close()

    print("\n🎉 所有验证通过！V0.2 → V0.3 迁移安全。")


if __name__ == "__main__":
    main()