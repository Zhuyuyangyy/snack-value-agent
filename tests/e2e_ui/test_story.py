from playwright.sync_api import Page


def test_story_visible(page: Page):
    assert page.locator("section.story").is_visible()


def test_story_three_cards(page: Page):
    cards = page.locator("section.story .story-card")
    assert cards.count() == 3


def test_story_keywords(page: Page):
    text = page.locator("section.story").inner_text()
    assert "克单价" in text
    assert "口味" in text
    assert "临期" in text
