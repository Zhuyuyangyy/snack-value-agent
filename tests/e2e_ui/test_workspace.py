from playwright.sync_api import Page


def test_workspace_visible(page: Page):
    assert page.locator("section.workspace").is_visible()


def test_workspace_add_item(page: Page):
    initial = page.locator("section.workspace .item-row").count()
    page.locator("section.workspace button:has-text('添加商品')").click()
    assert page.locator("section.workspace .item-row").count() == initial + 1


def test_workspace_compare_renders_result(page: Page):
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("A")
    rows.nth(0).locator(".f-price").fill("9.9")
    rows.nth(0).locator(".f-weight").fill("100")
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows.nth(1).locator(".f-name").fill("B")
    rows.nth(1).locator(".f-price").fill("12.9")
    rows.nth(1).locator(".f-weight").fill("100")
    page.locator("section.workspace button:has-text('开始比价')").click()
    page.wait_for_selector("section.result .rec-card-primary, .rec-card-secondary", timeout=15000)
    assert page.locator("section.result").is_visible()
