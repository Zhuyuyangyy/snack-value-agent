from playwright.sync_api import Page


def test_result_section_exists(page: Page):
    assert page.locator("section.result").count() > 0


def test_result_after_compare_shows_rec_card(page: Page):
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("A")
    rows.nth(0).locator(".f-price").fill("9.9")
    rows.nth(0).locator(".f-weight").fill("100")
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows.nth(1).locator(".f-name").fill("B")
    rows.nth(1).locator(".f-price").fill("19.9")
    rows.nth(1).locator(".f-weight").fill("100")
    page.locator("section.workspace button:has-text('开始比价')").click()
    page.wait_for_selector("section.result .rec-card-primary, .rec-card-secondary", timeout=15000)
    assert page.locator(".rec-card-primary, .rec-card-secondary").count() >= 1
