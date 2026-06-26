"""Hero section 验证。"""
from playwright.sync_api import Page


def test_hero_visible(page: Page):
    hero = page.locator("section.hero")
    assert hero.is_visible()


def test_hero_title(page: Page):
    title = page.locator("section.hero h1.hero-title").inner_text()
    assert "10 秒" in title
    assert "临期零食" in title


def test_hero_primary_cta(page: Page):
    cta = page.locator("section.hero button.btn-primary")
    assert cta.is_visible()


def test_hero_full_viewport(page: Page):
    box = page.locator("section.hero").bounding_box()
    viewport_height = page.viewport_size["height"]
    assert box["height"] >= viewport_height * 0.9
