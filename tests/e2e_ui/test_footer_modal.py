from playwright.sync_api import Page


def test_footer_visible(page: Page):
    assert page.locator("footer.site-footer").is_visible()


def test_preference_modal_exists(page: Page):
    assert page.locator("#prefModal").count() > 0


def test_preference_modal_opens(page: Page):
    page.locator("button:has-text('偏好'), button:has-text('⚙')").first.click()
    page.wait_for_timeout(300)
    modal = page.locator("#prefModal")
    is_visible = modal.is_visible() or modal.evaluate("el => getComputedStyle(el).display !== 'none'")
    assert is_visible
