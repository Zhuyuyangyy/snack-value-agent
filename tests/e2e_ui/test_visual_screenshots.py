"""视觉回归：保存截图供人工对比。"""
from pathlib import Path
import pytest
from playwright.sync_api import Page


SHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "superpowers" / "ui-screenshots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("viewport", [
    ("desktop", 1440, 900),
    ("tablet", 1024, 768),
    ("mobile", 390, 844),
])
def test_capture_homepage(browser, server_url, viewport):
    name, w, h = viewport
    context = browser.new_context(viewport={"width": w, "height": h})
    p = context.new_page()
    p.goto(server_url)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)
    shot = SHOTS_DIR / f"homepage-{name}.png"
    p.screenshot(path=str(shot), full_page=True)
    context.close()
    assert shot.exists()
    assert shot.stat().st_size > 5000


def test_capture_after_compare(browser, server_url):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    p = context.new_page()
    p.goto(server_url)
    p.wait_for_load_state("networkidle")
    # Add 2 items with full V0.3 fields
    p.locator("section.workspace button:has-text('添加商品')").click()
    p.locator("section.workspace button:has-text('添加商品')").click()
    rows = p.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("奥利奥 A")
    rows.nth(0).locator(".f-price").fill("19.9")
    rows.nth(0).locator(".f-weight").fill("100")
    rows.nth(0).locator(".f-expiry").fill("2026-09-01")
    rows.nth(0).locator(".f-flavor-type").select_option("fixed")
    rows.nth(1).locator(".f-name").fill("乐事 B")
    rows.nth(1).locator(".f-price").fill("12.9")
    rows.nth(1).locator(".f-weight").fill("100")
    rows.nth(1).locator(".f-expiry").fill("2026-08-01")
    rows.nth(1).locator(".f-flavor-type").select_option("random")
    p.locator("section.workspace button:has-text('开始比价')").click()
    p.wait_for_selector("section.result .rec-card-primary", timeout=15000)
    p.wait_for_timeout(800)
    shot = SHOTS_DIR / "after-compare.png"
    p.screenshot(path=str(shot), full_page=True)
    context.close()
    assert shot.stat().st_size > 5000