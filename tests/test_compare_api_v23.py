"""/api/compare 新字段接收测试。"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client():
    from backend.app import app
    from backend import database as db
    db.init_db()  # ensure schema before TestClient fires startup
    with TestClient(app) as c:
        yield c


def test_compare_accepts_new_price_fields(client: TestClient):
    """新价格字段被接受并存储。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "测试A",
            "final_price": 19.9,
            "listed_price": 29.9,
            "coupon_amount": 10.0,
            "shipping_fee": 0,
            "total_weight_g": 100,
            "flavor_type": "fixed"
        }],
        "save": False
    })
    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "测试A"


def test_compare_accepts_logistics_fields(client: TestClient):
    """物流字段：channel / category / brand。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100,
            "channel": "jd",
            "category": "chips",
            "brand": "乐事"
        }],
        "save": False
    })
    assert res.status_code == 200


def test_compare_legacy_total_price_still_works(client: TestClient):
    """老请求（仅 total_price）仍兼容：自动映射到 final_price。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "老格式",
            "total_price": 9.9,
            "total_weight_g": 100
        }],
        "save": False
    })
    assert res.status_code == 200


def test_compare_validates_final_price_positive(client: TestClient):
    """final_price = 0 应 422。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 0,
            "total_weight_g": 100
        }],
        "save": False
    })
    assert res.status_code == 422


def test_compare_validates_flavor_type_enum(client: TestClient):
    """flavor_type 非法值应 422。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100,
            "flavor_type": "weird_value"
        }],
        "save": False
    })
    assert res.status_code == 422


def test_compare_with_expiry_and_delivery_days(client: TestClient):
    """带 expiry_date 和 estimated_delivery_days 的请求。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "临期薯片",
            "final_price": 9.9,
            "total_weight_g": 100,
            "expiry_date": "2026-12-01",
            "estimated_delivery_days": 3
        }],
        "save": False
    })
    assert res.status_code == 200


def test_compare_with_full_v03_fields(client: TestClient):
    """全 V0.3 字段请求（确保不报 500）。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "全字段",
            "final_price": 19.9,
            "listed_price": 29.9,
            "coupon_amount": 10,
            "shipping_fee": 0,
            "total_weight_g": 100,
            "quantity": 5,
            "flavor_type": "random",
            "flavor_name": "随机",
            "expiry_date": "2026-09-01",
            "estimated_delivery_days": 3,
            "channel": "tmall",
            "category": "chips",
            "brand": "乐事",
            "after_opening_risk": "medium"
        }],
        "save": False
    })
    assert res.status_code == 200


def test_compare_missing_required_fields_returns_422(client: TestClient):
    """缺 final_price + total_price 应 422。"""
    res = client.post("/api/compare", json={
        "items": [{"name": "X"}],
        "save": False
    })
    assert res.status_code == 422


def test_compare_with_4score_fields_in_response(client: TestClient):
    """响应应包含 V0.3 4 评分字段。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100,
            "flavor_type": "fixed"
        }],
        "save": False
    })
    assert res.status_code == 200
    r = res.json()["results"][0]


def test_compare_response_includes_v03_fields(client: TestClient):
    """响应包含 V0.3 4 评分 + real_value 字段。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100,
            "flavor_type": "fixed"
        }],
        "save": False
    })
    assert res.status_code == 200
    r = res.json()["results"][0]
    # V0.3 字段必须存在
    for field in ["price_per_100g", "required_daily_intake_g",
                  "real_value_price_per_g",
                  "price_score", "expiry_score", "preference_score", "trust_score",
                  "final_score", "missing_fields", "field_confidences"]:
        assert field in r, f"响应缺少 V0.3 字段: {field}"


def test_compare_response_includes_legacy_fields(client: TestClient):
    """响应也保留 V0.2 旧字段（向后兼容）。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100,
            "flavor_type": "fixed"
        }],
        "save": False
    })
    r = res.json()["results"][0]
    for field in ["name", "total_price", "price_per_g", "value_score",
                  "recommendation_label", "reason", "risk_level"]:
        assert field in r, f"响应缺少 V0.2 字段: {field}"


def test_compare_missing_fields_list_populated(client: TestClient):
    """缺字段时 missing_fields 列表非空。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100
        }],
        "save": False
    })
    r = res.json()["results"][0]
    assert "missing_fields" in r
    assert isinstance(r["missing_fields"], list)
    assert len(r["missing_fields"]) > 0  # 至少缺 expiry_date 等


def test_compare_with_4score_response(client: TestClient):
    """请求含 expiry 时，4 评分应计算（非 None）。"""
    res = client.post("/api/compare", json={
        "items": [{
            "name": "X",
            "final_price": 10,
            "total_weight_g": 100,
            "flavor_type": "fixed",
            "expiry_date": "2026-09-01",
            "estimated_delivery_days": 3
        }],
        "save": False
    })
    r = res.json()["results"][0]
    # 评分应是 0-1 浮点数
    assert isinstance(r["price_score"], (int, float))
    assert 0 <= r["price_score"] <= 1
    assert isinstance(r["expiry_score"], (int, float))
    assert 0 <= r["expiry_score"] <= 1
    assert isinstance(r["preference_score"], (int, float))
    assert isinstance(r["trust_score"], (int, float))
    assert isinstance(r["final_score"], (int, float))