"""V0.4 商业化基础设施：API Key 认证 + 每日配额 + 用量计量。

设计原则：
- 默认零门槛：SNACKVALUE_API_KEYS 未配置时为「开放模式」，行为与 V0.3 完全一致
  （不校验 key，不限量），本地个人用户无感知。
- 配置即商业化：托管部署时配置 key 列表 + 每日配额，即获得
  免费层限流 / 付费层放量的最小闭环；用量落在 SQLite，可直接对账。
- 计量端点：仅对有算力/推理成本的端点计量（compare / extract / extract_text），
  读接口（baseline / history / preference / usage / stats）只认证不计量。
"""
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from . import config
from .database import DEFAULT_DB_PATH, _connect

# 开放模式下用量归到统一的匿名主体，便于统计总调用量
ANONYMOUS_KEY = "anonymous"

# V0.5：签发 key 的可辨识前缀（日志脱敏、支持渠道排查时一眼可识别）
KEY_PREFIX = "sv-"

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


def _ensure_keys_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            api_key     TEXT PRIMARY KEY,
            label       TEXT,
            tier        TEXT NOT NULL DEFAULT 'free',
            daily_quota INTEGER,
            created_at  TEXT NOT NULL,
            revoked_at  TEXT
        )
        """
    )


def lookup_db_key(api_key: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[dict]:
    """查 api_keys 表中的 key。返回 dict（含 revoked_at），不存在返回 None。"""
    conn = _connect(db_path)
    _ensure_keys_table(conn)
    row = conn.execute(
        "SELECT api_key, label, tier, daily_quota, created_at, revoked_at FROM api_keys WHERE api_key = ?",
        (api_key,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _db_keys_exist(db_path: Path = DEFAULT_DB_PATH) -> bool:
    """api_keys 表是否有过任何记录（含已吊销）。

    故意不过滤 revoked_at：一旦开始用 DB key 运营，吊销最后一个 key 也不能
    让服务退回开放模式，否则付费墙会被一次吊销操作意外拆掉。回到开放模式
    的唯一方式是显式清空 api_keys 表。
    """
    conn = _connect(db_path)
    _ensure_keys_table(conn)
    row = conn.execute("SELECT 1 FROM api_keys LIMIT 1").fetchone()
    conn.close()
    return row is not None


def require_api_key(api_key: Optional[str] = Security(_api_key_header)) -> str:
    """FastAPI 依赖：校验 X-API-Key。

    认证在以下任一条件满足时启用：配置了 SNACKVALUE_API_KEYS，或 api_keys 表
    非空（V0.5 支付下发场景，含已吊销记录）。两者都没有 = 开放模式直接放行。
    env key 与 DB key 同时有效；DB key 被吊销后立即失效。
    """
    env_keys = config.api_keys()
    if not env_keys and not _db_keys_exist():
        return ANONYMOUS_KEY
    if api_key is None:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")
    if api_key in env_keys:
        return api_key
    db_key = lookup_db_key(api_key)
    if db_key is not None and db_key["revoked_at"] is None:
        return api_key
    raise HTTPException(status_code=401, detail="X-API-Key 无效或已吊销")


def resolve_daily_quota(api_key: str, db_path: Path = DEFAULT_DB_PATH) -> int:
    """该 key 的每日配额：api_keys.daily_quota 优先，NULL/env key 用全局默认。0 = 不限。"""
    db_key = lookup_db_key(api_key, db_path)
    if db_key is not None and db_key["daily_quota"] is not None:
        return db_key["daily_quota"]
    return config.daily_quota()


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
    配额取 per-key 覆盖值（api_keys.daily_quota），无覆盖用全局默认。
    """
    quota = resolve_daily_quota(api_key, db_path)
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


# ---------------------------------------------------------------------- #
# V0.5 key 生命周期：签发 / 列表 / 吊销（支付闭环的对接点——
# 支付成功回调只需调 issue_key，退款/到期调 revoke_key）
# ---------------------------------------------------------------------- #
_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin_key(admin_key: Optional[str] = Security(_admin_key_header)) -> str:
    """管理端认证：X-Admin-Key 必须等于 SNACKVALUE_ADMIN_KEY。

    未配置 SNACKVALUE_ADMIN_KEY 时管理端整体关闭（403），避免误暴露。
    """
    expected = config.admin_key()
    if not expected:
        raise HTTPException(status_code=403, detail="管理端未启用：请配置 SNACKVALUE_ADMIN_KEY")
    if admin_key is None or not secrets.compare_digest(admin_key, expected):
        raise HTTPException(status_code=401, detail="X-Admin-Key 无效")
    return admin_key


def issue_key(label: str = "", tier: str = "free", daily_quota: Optional[int] = None,
              db_path: Path = DEFAULT_DB_PATH) -> dict:
    """签发一个新 API Key 并入库，返回完整 key 信息（key 仅此一次完整下发）。"""
    if tier not in {"free", "pro"}:
        raise ValueError("tier 必须是 free 或 pro")
    if daily_quota is not None and daily_quota < 0:
        raise ValueError("daily_quota 不能为负数")
    new_key = KEY_PREFIX + secrets.token_urlsafe(24)
    conn = _connect(db_path)
    _ensure_keys_table(conn)
    conn.execute(
        "INSERT INTO api_keys (api_key, label, tier, daily_quota, created_at) VALUES (?, ?, ?, ?, ?)",
        (new_key, label, tier, daily_quota, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {
        "api_key": new_key,
        "label": label,
        "tier": tier,
        "daily_quota": daily_quota,
    }


def list_keys(db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """列出全部 key（含已吊销）及其今日/累计用量，key 做脱敏展示。"""
    conn = _connect(db_path)
    _ensure_keys_table(conn)
    _ensure_usage_table(conn)
    rows = conn.execute(
        """
        SELECT k.api_key, k.label, k.tier, k.daily_quota, k.created_at, k.revoked_at,
               COALESCE(t.today_count, 0) AS usage_today,
               COALESCE(a.total_count, 0) AS usage_total
        FROM api_keys k
        LEFT JOIN (
            SELECT api_key, SUM(count) AS today_count FROM api_usage
            WHERE usage_date = ? GROUP BY api_key
        ) t ON t.api_key = k.api_key
        LEFT JOIN (
            SELECT api_key, SUM(count) AS total_count FROM api_usage GROUP BY api_key
        ) a ON a.api_key = k.api_key
        ORDER BY k.created_at DESC
        """,
        (date.today().isoformat(),),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # 脱敏：只保留前缀 + 前 4 位 + 后 4 位
        full = d["api_key"]
        d["api_key_masked"] = f"{full[:len(KEY_PREFIX) + 4]}...{full[-4:]}"
        del d["api_key"]
        result.append(d)
    return result


def revoke_key(api_key: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    """吊销一个 key（幂等）。返回是否找到并吊销了未吊销的 key。

    注意：吊销不会让服务退回开放模式（见 _db_keys_exist）；
    需要开放模式请用 purge_keys 清空整表。
    """
    conn = _connect(db_path)
    _ensure_keys_table(conn)
    cur = conn.execute(
        "UPDATE api_keys SET revoked_at = ? WHERE api_key = ? AND revoked_at IS NULL",
        (datetime.now().isoformat(), api_key),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def purge_keys(db_path: Path = DEFAULT_DB_PATH) -> int:
    """删除全部 DB key 记录，服务回到开放模式（仅运维 CLI 用，不暴露 HTTP）。"""
    conn = _connect(db_path)
    _ensure_keys_table(conn)
    cur = conn.execute("DELETE FROM api_keys")
    conn.commit()
    conn.close()
    return cur.rowcount
