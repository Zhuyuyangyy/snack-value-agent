import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend import style_advice


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def force_fallback(monkeypatch):
    """Disable real Gemini calls in tests; force rule fallback."""
    monkeypatch.setattr(style_advice, "_call_gemini", None)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_style_advice_minimal_payload(client):
    payload = {
        "items": [
            {
                "id": "a", "name": "x", "category": "top", "slot": "upper",
                "price": 30, "styleTags": ["学院"], "riskTags": [],
                "photoScore": 70, "dailyScore": 70, "qualityScore": 70,
            }
        ],
        "intent": None,
    }
    r = client.post("/api/style-advice", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "rule-fallback"
    assert 0 <= body["scores"]["styleConsistency"] <= 100
    assert "scores" in body
    assert all(k in body["scores"] for k in [
        "styleConsistency", "colorHarmony", "layerCompleteness",
        "photoScore", "dailyScore", "riskScore",
    ])


def test_style_advice_empty_items(client):
    r = client.post("/api/style-advice", json={"items": [], "intent": None})
    assert r.status_code == 200
    body = r.json()
    assert body["scores"]["layerCompleteness"] == 0


def test_cors_header_allows_localhost(client):
    r = client.options(
        "/api/style-advice",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.headers.get("access-control-allow-origin") in {
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    }


def test_rate_limit_returns_429_after_threshold(client, monkeypatch):
    """Verify rate limiter is active (10/min per IP)."""
    # Slowapi stores per-endpoint limits on Limiter._route_limits keyed by the
    # endpoint function's __qualname__. Patch the underlying Limit object so we
    # can exercise the 429 path without firing 11 real requests.
    from backend.app import limiter
    from limits import parse

    endpoint_fn = "backend.app.style_advice_endpoint"
    limits = limiter._route_limits.get(endpoint_fn, [])
    assert limits, "endpoint should be registered with the rate limiter"
    # Reset storage so prior tests don't pollute counts.
    limiter._storage.reset()
    # Tighten to 2/minute and reset between requests to count cleanly.
    original_limit = limits[0].limit
    limits[0].limit = parse("2/minute")
    try:
        payload = {"items": [], "intent": None}
        statuses = [client.post("/api/style-advice", json=payload).status_code for _ in range(5)]
        assert 429 in statuses, f"expected 429 among statuses, got {statuses}"
    finally:
        # Restore original limit and clear storage so other tests aren't affected.
        limits[0].limit = original_limit
        limiter._storage.reset()
