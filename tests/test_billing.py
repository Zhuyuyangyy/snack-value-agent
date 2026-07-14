"""V0.4 商业化基础设施测试：API Key 认证 / 每日配额 / 用量计量 / 经营指标。"""
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config
from backend.database import _connect, init_db, load_stats


@pytest.fixture
def client(monkeypatch):
    """默认开放模式的 TestClient（清掉可能存在的商业化 env；
    残留 DB key 由 tests/conftest.py 的 autouse 基线清理）。"""
    monkeypatch.delenv("SNACKVALUE_API_KEYS", raising=False)
    monkeypatch.delenv("SNACKVALUE_DAILY_QUOTA", raising=False)
    from backend.app import app
    from backend import database as db
    db.init_db()
    with TestClient(app) as c:
        yield c


def _fresh_key() -> str:
    """每个测试用唯一 key，避免共享 DB 里的历史用量互相干扰。"""
    return f"test-{uuid.uuid4().hex[:12]}"


COMPARE_BODY = {
    "items": [{"name": "配额测试", "final_price": 10, "total_weight_g": 100}],
    "save": False,
}


# ---------------------------------------------------------------------- #
# config
# ---------------------------------------------------------------------- #
def test_config_defaults_open_mode(monkeypatch):
    monkeypatch.delenv("SNACKVALUE_API_KEYS", raising=False)
    monkeypatch.delenv("SNACKVALUE_DAILY_QUOTA", raising=False)
    monkeypatch.delenv("SNACKVALUE_CORS_ORIGINS", raising=False)
    assert config.api_keys() == set()
    assert config.daily_quota() == 0
    assert config.cors_origins() == []


def test_config_parses_comma_lists(monkeypatch):
    monkeypatch.setenv("SNACKVALUE_API_KEYS", "key-a, key-b ,,")
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "50")
    monkeypatch.setenv("SNACKVALUE_CORS_ORIGINS", "https://a.com, https://b.com")
    assert config.api_keys() == {"key-a", "key-b"}
    assert config.daily_quota() == 50
    assert config.cors_origins() == ["https://a.com", "https://b.com"]


def test_db_path_env_override(monkeypatch, tmp_path):
    from backend.database import _default_db_path
    custom = tmp_path / "custom.db"
    monkeypatch.setenv("SNACKVALUE_DB_PATH", str(custom))
    assert _default_db_path() == custom
    monkeypatch.delenv("SNACKVALUE_DB_PATH")
    assert _default_db_path().name == "snack_history.db"


# ---------------------------------------------------------------------- #
# 开放模式（向后兼容）
# ---------------------------------------------------------------------- #
def test_open_mode_no_key_required(client: TestClient):
    assert client.post("/api/compare", json=COMPARE_BODY).status_code == 200
    assert client.get("/api/history").status_code == 200


def test_open_mode_usage_endpoint(client: TestClient):
    res = client.get("/api/usage")
    assert res.status_code == 200
    data = res.json()
    assert data["api_key_mode"] is False
    assert data["daily_quota"] is None
    assert data["remaining"] is None
    assert "total" in data["usage"]


def test_health_reports_version(client: TestClient):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["version"]


# ---------------------------------------------------------------------- #
# API Key 认证模式
# ---------------------------------------------------------------------- #
def test_key_mode_rejects_missing_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("SNACKVALUE_API_KEYS", _fresh_key())
    assert client.post("/api/compare", json=COMPARE_BODY).status_code == 401
    assert client.get("/api/history").status_code == 401


def test_key_mode_rejects_wrong_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("SNACKVALUE_API_KEYS", _fresh_key())
    res = client.post("/api/compare", json=COMPARE_BODY, headers={"X-API-Key": "wrong"})
    assert res.status_code == 401


def test_key_mode_accepts_valid_key(client: TestClient, monkeypatch):
    key = _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", f"{key},other-key")
    headers = {"X-API-Key": key}
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 200
    assert client.get("/api/usage", headers=headers).status_code == 200


def test_key_mode_health_stays_open(client: TestClient, monkeypatch):
    monkeypatch.setenv("SNACKVALUE_API_KEYS", _fresh_key())
    assert client.get("/api/health").status_code == 200


# ---------------------------------------------------------------------- #
# 每日配额
# ---------------------------------------------------------------------- #
def test_quota_blocks_after_limit(client: TestClient, monkeypatch):
    key = _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", key)
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "2")
    headers = {"X-API-Key": key}
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 200
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 200
    res = client.post("/api/compare", json=COMPARE_BODY, headers=headers)
    assert res.status_code == 429
    assert "配额" in res.json()["detail"]


def test_quota_counts_across_metered_endpoints(client: TestClient, monkeypatch):
    """compare 与 extract_text 共享同一日配额池。"""
    key = _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", key)
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "2")
    headers = {"X-API-Key": key}
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 200
    assert client.post("/api/extract_text", json={"text": "奥利奥 19.9元 420g"}, headers=headers).status_code == 200
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 429


def test_quota_is_per_key(client: TestClient, monkeypatch):
    key_a, key_b = _fresh_key(), _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", f"{key_a},{key_b}")
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "1")
    assert client.post("/api/compare", json=COMPARE_BODY, headers={"X-API-Key": key_a}).status_code == 200
    assert client.post("/api/compare", json=COMPARE_BODY, headers={"X-API-Key": key_a}).status_code == 429
    # 另一个 key 有独立配额
    assert client.post("/api/compare", json=COMPARE_BODY, headers={"X-API-Key": key_b}).status_code == 200


def test_quota_read_endpoints_not_metered(client: TestClient, monkeypatch):
    """读接口（history/usage/stats）不消耗配额。"""
    key = _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", key)
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "1")
    headers = {"X-API-Key": key}
    for _ in range(3):
        assert client.get("/api/history", headers=headers).status_code == 200
        assert client.get("/api/stats", headers=headers).status_code == 200
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 200


def test_usage_endpoint_reports_remaining(client: TestClient, monkeypatch):
    key = _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", key)
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "5")
    headers = {"X-API-Key": key}
    client.post("/api/compare", json=COMPARE_BODY, headers=headers)
    client.post("/api/compare", json=COMPARE_BODY, headers=headers)
    data = client.get("/api/usage", headers=headers).json()
    assert data["api_key_mode"] is True
    assert data["daily_quota"] == 5
    assert data["usage"]["total"] == 2
    assert data["usage"]["by_endpoint"] == {"compare": 2}
    assert data["remaining"] == 3


def test_rejected_request_does_not_consume_quota(client: TestClient, monkeypatch):
    """422（items 为空）发生在计量之前，不应消耗配额。"""
    key = _fresh_key()
    monkeypatch.setenv("SNACKVALUE_API_KEYS", key)
    monkeypatch.setenv("SNACKVALUE_DAILY_QUOTA", "1")
    headers = {"X-API-Key": key}
    assert client.post("/api/compare", json={"items": [], "save": False}, headers=headers).status_code == 422
    assert client.post("/api/compare", json=COMPARE_BODY, headers=headers).status_code == 200


# ---------------------------------------------------------------------- #
# /api/stats 经营指标
# ---------------------------------------------------------------------- #
def _insert_history(db_path: Path, *, price_per_g: float, weight: float,
                    total_price=None, listed_price=None, created_at=None):
    conn = _connect(db_path)
    conn.execute(
        """
        INSERT INTO snack_history (
            name, total_price, listed_price, total_weight_g, flavor_type,
            price_per_g, adjusted_price_per_g, created_at
        ) VALUES (?, ?, ?, ?, 'fixed', ?, ?, ?)
        """,
        ("统计测试", total_price, listed_price, weight, price_per_g, price_per_g,
         created_at or datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def test_stats_empty_db(tmp_path):
    db_path = tmp_path / "stats.db"
    init_db(db_path)
    stats = load_stats(db_path)
    assert stats["total_evaluations"] == 0
    assert stats["discount_savings"] == 0
    assert stats["estimated_savings_vs_avg"] == 0
    assert stats["avg_price_per_g"] is None


def test_stats_aggregates(tmp_path):
    db_path = tmp_path / "stats.db"
    init_db(db_path)
    # 两条记录：一条有折扣（省 10 元），克单价 0.04 与 0.06
    _insert_history(db_path, price_per_g=0.04, weight=500, total_price=20, listed_price=30)
    _insert_history(db_path, price_per_g=0.06, weight=200, total_price=12)
    stats = load_stats(db_path)
    assert stats["total_evaluations"] == 2
    assert stats["total_weight_g"] == 700
    assert stats["active_days"] == 1
    assert stats["evaluations_last_7_days"] == 2
    assert stats["min_price_per_g"] == 0.04
    assert stats["avg_price_per_g"] == 0.05
    assert stats["discount_savings"] == 10
    # 比平均便宜的那单：(0.05 - 0.04) × 500 = 5 元
    assert stats["estimated_savings_vs_avg"] == 5
    assert stats["min_price_per_g"] <= stats["avg_price_per_g"]


def test_stats_endpoint_shape(client: TestClient):
    data = client.get("/api/stats").json()
    for field in (
        "total_evaluations", "total_weight_g", "active_days",
        "evaluations_last_7_days", "avg_price_per_g", "min_price_per_g",
        "discount_savings", "estimated_savings_vs_avg",
    ):
        assert field in data
