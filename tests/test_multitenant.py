"""V0.5 多租户与 key 生命周期测试：数据隔离 / v0.4→v0.5 迁移 / admin API / CLI。"""
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.billing import KEY_PREFIX, purge_keys
from backend.database import (
    DEFAULT_DB_PATH,
    _connect,
    init_db,
    load_baseline,
    load_history,
    load_user_preference,
    migrate_v05,
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("SNACKVALUE_API_KEYS", raising=False)
    monkeypatch.delenv("SNACKVALUE_DAILY_QUOTA", raising=False)
    monkeypatch.delenv("SNACKVALUE_ADMIN_KEY", raising=False)
    from backend.app import app
    from backend import database as db
    db.init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def issued_keys():
    """测试内签发的 DB key 收集器；测试结束硬删除记录，把共享 DB 还原成开放模式。

    （吊销不够：只要表里有记录服务就保持认证模式，会影响其他开放模式测试。）
    """
    created: list[str] = []
    yield created
    conn = _connect(DEFAULT_DB_PATH)
    for k in created:
        conn.execute("DELETE FROM api_keys WHERE api_key = ?", (k,))
    conn.commit()
    conn.close()


@pytest.fixture
def admin(monkeypatch):
    admin_key = f"admin-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("SNACKVALUE_ADMIN_KEY", admin_key)
    return {"X-Admin-Key": admin_key}


def _compare_body(name: str, price: float, weight: float) -> dict:
    return {"items": [{"name": name, "final_price": price, "total_weight_g": weight}], "save": True}


# ---------------------------------------------------------------------- #
# V0.4 → V0.5 迁移
# ---------------------------------------------------------------------- #
def _make_v04_db(db_path: Path) -> None:
    """构造 V0.4 老库：单例 baseline / user_preference + 无 api_key 列的 history。"""
    conn = _connect(db_path)
    conn.executescript("""
        CREATE TABLE snack_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            total_price REAL,
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
            id INTEGER PRIMARY KEY CHECK (id = 1),
            baseline_price_per_g REAL NOT NULL,
            baseline_source TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE user_preference (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            preferred_flavors TEXT,
            disliked_flavors TEXT,
            daily_intake_g REAL DEFAULT 20.0
        );
        INSERT INTO snack_history (name, total_price, total_weight_g, flavor_type,
                                   price_per_g, adjusted_price_per_g, created_at)
        VALUES ('老数据', 10, 200, 'fixed', 0.05, 0.05, '2026-01-01T00:00:00');
        INSERT INTO baseline VALUES (1, 0.05, '老数据', '2026-01-01T00:00:00');
        INSERT INTO user_preference VALUES (1, '["原味"]', '["辣味"]', 30.0);
    """)
    conn.commit()
    conn.close()


def test_migrate_v05_moves_singleton_data_to_anonymous(tmp_path):
    db_path = tmp_path / "v04.db"
    _make_v04_db(db_path)
    init_db(db_path)

    price, source = load_baseline(db_path, api_key="anonymous")
    assert price == 0.05
    assert source == "老数据"

    pref = load_user_preference(db_path, api_key="anonymous")
    assert pref["preferred_flavors"] == ["原味"]
    assert pref["daily_intake_g"] == 30.0

    history = load_history(db_path=db_path, api_key="anonymous")
    assert len(history) == 1
    assert history[0]["name"] == "老数据"


def test_migrate_v05_is_idempotent(tmp_path):
    db_path = tmp_path / "v04.db"
    _make_v04_db(db_path)
    init_db(db_path)
    migrate_v05(db_path)  # 再跑一次不炸、不丢数据
    price, _ = load_baseline(db_path, api_key="anonymous")
    assert price == 0.05


def test_other_tenant_sees_nothing_after_migration(tmp_path):
    db_path = tmp_path / "v04.db"
    _make_v04_db(db_path)
    init_db(db_path)
    price, source = load_baseline(db_path, api_key="sv-someone-else")
    assert price == float("inf")
    assert load_history(db_path=db_path, api_key="sv-someone-else") == []


# ---------------------------------------------------------------------- #
# 租户数据隔离（HTTP 层）
# ---------------------------------------------------------------------- #
def test_tenants_have_isolated_preference_and_history(client, monkeypatch):
    key_a = f"tenant-a-{uuid.uuid4().hex[:8]}"
    key_b = f"tenant-b-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("SNACKVALUE_API_KEYS", f"{key_a},{key_b}")
    ha, hb = {"X-API-Key": key_a}, {"X-API-Key": key_b}

    # A 设置偏好；B 看不到
    client.put("/api/preference", json={"preferred_flavors": ["抹茶"], "disliked_flavors": [], "daily_intake_g": 25}, headers=ha)
    assert client.get("/api/preference", headers=ha).json()["preferred_flavors"] == ["抹茶"]
    assert client.get("/api/preference", headers=hb).json()["preferred_flavors"] == []

    # A 比价并落库；B 的历史和基线不受影响
    unique = f"隔离-{uuid.uuid4().hex[:6]}"
    client.post("/api/compare", json=_compare_body(unique, 9.9, 330), headers=ha)
    names_a = [h["name"] for h in client.get("/api/history", headers=ha).json()]
    names_b = [h["name"] for h in client.get("/api/history", headers=hb).json()]
    assert unique in names_a
    assert unique not in names_b
    assert client.get("/api/baseline", headers=hb).json()["baseline_price_per_g"] is None

    # stats 也按租户
    assert client.get("/api/stats", headers=hb).json()["total_evaluations"] == 0


# ---------------------------------------------------------------------- #
# Admin API：key 生命周期
# ---------------------------------------------------------------------- #
def test_admin_disabled_without_env(client):
    assert client.get("/api/admin/keys").status_code == 403


def test_admin_rejects_wrong_key(client, admin):
    assert client.get("/api/admin/keys", headers={"X-Admin-Key": "wrong"}).status_code == 401


def test_admin_issue_key_enables_auth_and_key_works(client, admin, issued_keys):
    res = client.post("/api/admin/keys", json={"label": "内测用户", "tier": "pro"}, headers=admin)
    assert res.status_code == 201
    key = res.json()["api_key"]
    issued_keys.append(key)
    assert key.startswith(KEY_PREFIX)

    # 存在有效 DB key 后：无 key 请求被拒，签发的 key 可用
    assert client.get("/api/history").status_code == 401
    assert client.get("/api/history", headers={"X-API-Key": key}).status_code == 200

    # 列表脱敏且含用量字段
    keys = client.get("/api/admin/keys", headers=admin).json()["keys"]
    match = [k for k in keys if k["label"] == "内测用户"]
    assert match and "api_key" not in match[0]
    assert match[0]["api_key_masked"].startswith(KEY_PREFIX)
    assert "usage_today" in match[0]


def test_admin_revoke_key_takes_effect_immediately(client, admin, issued_keys):
    key = client.post("/api/admin/keys", json={"label": "将吊销"}, headers=admin).json()["api_key"]
    issued_keys.append(key)
    headers = {"X-API-Key": key}
    assert client.get("/api/history", headers=headers).status_code == 200

    res = client.delete(f"/api/admin/keys/{key}", headers=admin)
    assert res.status_code == 200
    assert client.get("/api/history", headers=headers).status_code == 401
    # 重复吊销幂等 → 404
    assert client.delete(f"/api/admin/keys/{key}", headers=admin).status_code == 404


def test_revoking_last_key_keeps_service_locked(client, admin, issued_keys):
    """商用保护：吊销最后一个 key 不能把付费墙拆掉，服务保持认证模式。"""
    key = client.post("/api/admin/keys", json={}, headers=admin).json()["api_key"]
    issued_keys.append(key)
    assert client.get("/api/history").status_code == 401
    client.delete(f"/api/admin/keys/{key}", headers=admin)
    assert client.get("/api/history").status_code == 401


def test_purge_keys_restores_open_mode(client, admin):
    client.post("/api/admin/keys", json={}, headers=admin)
    assert client.get("/api/history").status_code == 401
    purge_keys()
    assert client.get("/api/history").status_code == 200


def test_per_key_quota_override(client, admin, issued_keys):
    """全局不限量时，key 自带的 daily_quota=1 仍然生效。"""
    key = client.post("/api/admin/keys", json={"label": "小配额", "daily_quota": 1}, headers=admin).json()["api_key"]
    issued_keys.append(key)
    headers = {"X-API-Key": key}
    body = {"items": [{"name": "Q", "final_price": 5, "total_weight_g": 50}], "save": False}
    assert client.post("/api/compare", json=body, headers=headers).status_code == 200
    assert client.post("/api/compare", json=body, headers=headers).status_code == 429
    data = client.get("/api/usage", headers=headers).json()
    assert data["daily_quota"] == 1
    assert data["remaining"] == 0


def test_admin_create_key_validates_tier(client, admin):
    assert client.post("/api/admin/keys", json={"tier": "platinum"}, headers=admin).status_code == 422


def test_admin_global_stats(client, admin):
    res = client.get("/api/admin/stats", headers=admin)
    assert res.status_code == 200
    assert "total_evaluations" in res.json()


# ---------------------------------------------------------------------- #
# 运维 CLI
# ---------------------------------------------------------------------- #
def test_issue_key_cli_roundtrip(tmp_path):
    env_db = tmp_path / "cli.db"
    root = Path(__file__).resolve().parent.parent
    env = {"SNACKVALUE_DB_PATH": str(env_db), "PATH": "/usr/bin:/bin:/usr/local/bin"}

    out = subprocess.run(
        [sys.executable, "scripts/issue_key.py", "issue", "--label", "cli测试", "--tier", "pro", "--quota", "500"],
        capture_output=True, text=True, cwd=root, env=env,
    )
    assert out.returncode == 0, out.stderr
    key_line = [l for l in out.stdout.splitlines() if "api_key" in l][0]
    key = key_line.split(":", 1)[1].strip()
    assert key.startswith(KEY_PREFIX)

    out = subprocess.run([sys.executable, "scripts/issue_key.py", "list"],
                         capture_output=True, text=True, cwd=root, env=env)
    assert "cli测试" in out.stdout and "有效" in out.stdout

    out = subprocess.run([sys.executable, "scripts/issue_key.py", "revoke", key],
                         capture_output=True, text=True, cwd=root, env=env)
    assert out.returncode == 0
    out = subprocess.run([sys.executable, "scripts/issue_key.py", "list"],
                         capture_output=True, text=True, cwd=root, env=env)
    assert "已吊销" in out.stdout
