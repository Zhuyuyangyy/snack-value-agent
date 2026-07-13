"""V0.4 商业化基础设施：API Key 认证 + 每日配额 + 用量计量。

设计原则：
- 默认零门槛：SNACKVALUE_API_KEYS 未配置时为「开放模式」，行为与 V0.3 完全一致
  （不校验 key，不限量），本地个人用户无感知。
- 配置即商业化：托管部署时配置 key 列表 + 每日配额，即获得
  免费层限流 / 付费层放量的最小闭环；用量落在 SQLite，可直接对账。
- 计量端点：仅对有算力/推理成本的端点计量（compare / extract / extract_text），
  读接口（baseline / history / preference / usage / stats）只认证不计量。
"""
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from . import config
from .database import DEFAULT_DB_PATH, _connect

# 开放模式下用量归到统一的匿名主体，便于统计总调用量
ANONYMOUS_KEY = "anonymous"

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _ensure_usage_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_usage (
            api_key   TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            endpoint  TEXT NOT NULL,
            count     INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (api_key, usage_date, endpoint)
        )
        """
    )


def require_api_key(api_key: Optional[str] = Security(_api_key_header)) -> str:
    """FastAPI 依赖：校验 X-API-Key。

    开放模式（未配置 SNACKVALUE_API_KEYS）直接放行，返回匿名主体。
    """
    keys = config.api_keys()
    if not keys:
        return ANONYMOUS_KEY
    if api_key is None:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")
    if api_key not in keys:
        raise HTTPException(status_code=401, detail="X-API-Key 无效")
    return api_key


def usage_today(api_key: str, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """返回该 key 今日各端点用量与总量：{"by_endpoint": {...}, "total": n}。"""
    conn = _connect(db_path)
    _ensure_usage_table(conn)
    rows = conn.execute(
        "SELECT endpoint, count FROM api_usage WHERE api_key = ? AND usage_date = ?",
        (api_key, date.today().isoformat()),
    ).fetchall()
    conn.close()
    by_endpoint = {r["endpoint"]: r["count"] for r in rows}
    return {"by_endpoint": by_endpoint, "total": sum(by_endpoint.values())}


def check_and_record_usage(api_key: str, endpoint: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """计量一次调用；配额（>0）耗尽时抛 429，且不再计数。

    开放模式下也记录（归到 anonymous），保证 /api/stats 的调用量可信。
    """
    quota = config.daily_quota()
    today = date.today().isoformat()
    conn = _connect(db_path)
    _ensure_usage_table(conn)
    try:
        if quota > 0:
            row = conn.execute(
                "SELECT COALESCE(SUM(count), 0) AS total FROM api_usage WHERE api_key = ? AND usage_date = ?",
                (api_key, today),
            ).fetchone()
            if row["total"] >= quota:
                raise HTTPException(
                    status_code=429,
                    detail=f"今日调用配额已用完（{quota} 次/天），请明天再试或升级套餐",
                )
        conn.execute(
            """
            INSERT INTO api_usage (api_key, usage_date, endpoint, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(api_key, usage_date, endpoint) DO UPDATE SET count = count + 1
            """,
            (api_key, today, endpoint),
        )
        conn.commit()
    finally:
        conn.close()
