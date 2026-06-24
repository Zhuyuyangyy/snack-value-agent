"""历史基线持久化：记录历史最低克单价与历史购买商品，形成个人价格记忆。"""
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import SnackItem, EvaluationResult


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "snack_history.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = _connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS snack_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            total_price   REAL NOT NULL,
            total_weight_g REAL NOT NULL,
            flavor_type   TEXT NOT NULL,
            flavor_name   TEXT,
            expiry_date   TEXT,
            package_type  TEXT DEFAULT 'unknown',
            quantity      INTEGER,
            source_text   TEXT,
            price_per_g   REAL NOT NULL,
            adjusted_price_per_g REAL NOT NULL,
            value_score   REAL,
            risk_level    TEXT,
            recommendation_label TEXT,
            reason        TEXT,
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS baseline (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            baseline_price_per_g REAL NOT NULL,
            baseline_source TEXT,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_preference (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            preferred_flavors TEXT,
            disliked_flavors  TEXT,
            daily_intake_g     REAL DEFAULT 20.0
        );
        """
    )
    conn.commit()
    conn.close()


def save_evaluation(result: EvaluationResult, db_path: Path = DEFAULT_DB_PATH) -> int:
    """落库一条评估记录。"""
    conn = _connect(db_path)
    cur = conn.execute(
        """
        INSERT INTO snack_history (
            name, total_price, total_weight_g, flavor_type, flavor_name,
            expiry_date, package_type, quantity, source_text,
            price_per_g, adjusted_price_per_g, value_score, risk_level,
            recommendation_label, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.item.name,
            result.item.total_price,
            result.item.total_weight_g,
            result.item.flavor_type,
            result.item.flavor_name,
            result.item.expiry_date.isoformat() if result.item.expiry_date else None,
            result.item.package_type,
            result.item.quantity,
            result.item.source_text,
            result.price_per_g,
            result.adjusted_price_per_g,
            result.value_score,
            result.risk_level,
            result.recommendation_label,
            result.reason,
            datetime.now().isoformat(),
        ),
    )
    record_id = cur.lastrowid
    conn.commit()
    conn.close()
    return record_id


def load_baseline(db_path: Path = DEFAULT_DB_PATH) -> tuple[float, Optional[str]]:
    """读取历史最低克单价。无记录时返回 (inf, None)。"""
    conn = _connect(db_path)
    row = conn.execute("SELECT baseline_price_per_g, baseline_source FROM baseline WHERE id = 1").fetchone()
    conn.close()
    if row is None:
        return float("inf"), None
    return row["baseline_price_per_g"], row["baseline_source"]


def update_baseline(price_per_g: float, source: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """更新历史最低克单价基线。"""
    conn = _connect(db_path)
    conn.execute(
        """
        INSERT INTO baseline (id, baseline_price_per_g, baseline_source, updated_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            baseline_price_per_g = excluded.baseline_price_per_g,
            baseline_source = excluded.baseline_source,
            updated_at = excluded.updated_at
        """,
        (price_per_g, source, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def load_history(limit: int = 50, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """读取历史购买记录。"""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT * FROM snack_history ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_user_preference(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """读取用户偏好。"""
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT preferred_flavors, disliked_flavors, daily_intake_g FROM user_preference WHERE id = 1"
    ).fetchone()
    conn.close()
    if row is None:
        return {"preferred_flavors": [], "disliked_flavors": [], "daily_intake_g": 20.0}
    return {
        "preferred_flavors": json.loads(row["preferred_flavors"]) if row["preferred_flavors"] else [],
        "disliked_flavors": json.loads(row["disliked_flavors"]) if row["disliked_flavors"] else [],
        "daily_intake_g": row["daily_intake_g"],
    }


def save_user_preference(preferred: list[str], disliked: list[str], daily_intake: float, db_path: Path = DEFAULT_DB_PATH) -> None:
    """保存用户偏好。"""
    conn = _connect(db_path)
    conn.execute(
        """
        INSERT INTO user_preference (id, preferred_flavors, disliked_flavors, daily_intake_g)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            preferred_flavors = excluded.preferred_flavors,
            disliked_flavors = excluded.disliked_flavors,
            daily_intake_g = excluded.daily_intake_g
        """,
        (json.dumps(preferred, ensure_ascii=False), json.dumps(disliked, ensure_ascii=False), daily_intake),
    )
    conn.commit()
    conn.close()
