"""Nav 组件验证。"""
from playwright.sync_api import Page


def test_nav_visible(page: Page):
    nav = page.locator("nav.nav-sticky")
    assert nav.is_visible()


def test_nav_brand(page: Page):
    nav_text = page.locator("nav.nav-sticky").inner_text()
    assert "SnackValue" in nav_text or "Snack" in nav_text


def test_nav_anchor_links(page: Page):
    links = page.locator("nav.nav-sticky a[href^='#']")
    count = links.count()
    assert count >= 3
