from playwright.sync_api import Page


def test_trust_section_visible(page: Page):
    assert page.locator("section.trust").is_visible()


def test_trust_four_faqs(page: Page):
    faqs = page.locator("section.trust .faq")
    assert faqs.count() == 4


def test_trust_faq_topics(page: Page):
    text = page.locator("section.trust").inner_text()
    assert "克单价" in text
    assert "口味" in text
    assert "临期" in text
    assert "评分" in text or "基线" in text
