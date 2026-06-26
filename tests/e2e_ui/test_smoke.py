"""E2E 冒烟测试：验证 server + page 能正常加载。"""
from playwright.sync_api import Page


def test_server_responds_200(server_url: str):
    """server 启动后能响应 200。"""
    import urllib.request
    res = urllib.request.urlopen(f"{server_url}/api/health")
    assert res.status == 200
    assert b'"status":"ok"' in res.read()


def test_page_loads(page: Page):
    """首页能正常加载，body 可见。"""
    body_text = page.locator("body").inner_text()
    assert len(body_text) > 0


def test_api_health_endpoint(page: Page, server_url: str):
    """通过 page 访问 health API。"""
    response = page.request.get(f"{server_url}/api/health")
    assert response.status == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_compare_endpoint(page: Page, server_url: str):
    """通过 page 访问 /api/compare（V0.3 兼容老格式）。"""
    response = page.request.post(
        f"{server_url}/api/compare",
        data='{"items":[{"name":"测试","total_price":10,"total_weight_g":100}],"save":false}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200
    data = response.json()
    assert "results" in data
    # V0.3 字段存在
    r = data["results"][0]
    assert "real_value_price_per_g" in r
    assert "price_score" in r
    assert "final_score" in r
