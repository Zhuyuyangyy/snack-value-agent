"""V0.3 多维度决策卡片验证。"""
from playwright.sync_api import Page


def test_rec_card_has_6_stat_blocks(page: Page):
    """主推荐卡片包含 6 个统计块（克单价/100g/单包/到期/口味/历史）。"""
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("测试")
    rows.nth(0).locator(".f-price").fill("19.9")
    rows.nth(0).locator(".f-weight").fill("100")
    rows.nth(0).locator(".f-expiry").fill("2026-09-01")
    page.locator("section.workspace button:has-text('开始比价')").click()
    page.wait_for_selector("section.result .rec-card-primary", timeout=15000)
    stat_blocks = page.locator("section.result .rec-card-primary .stat-block")
    assert stat_blocks.count() == 6, f"应有 6 个 stat-block，实际 {stat_blocks.count()}"


def test_rec_card_has_4_score_pills(page: Page):
    """主推荐卡片显示 4 个评分 pill。"""
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("测试")
    rows.nth(0).locator(".f-price").fill("19.9")
    rows.nth(0).locator(".f-weight").fill("100")
    rows.nth(0).locator(".f-expiry").fill("2026-09-01")
    page.locator("section.workspace button:has-text('开始比价')").click()
    page.wait_for_selector("section.result .rec-card-primary", timeout=15000)
    pills = page.locator("section.result .rec-card-primary .score-pill")
    assert pills.count() == 4, f"应有 4 个 score-pill，实际 {pills.count()}"


def test_missing_fields_warning_visible(page: Page):
    """缺字段时显示警告。"""
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("测试")
    rows.nth(0).locator(".f-price").fill("19.9")
    rows.nth(0).locator(".f-weight").fill("100")
    # 不填 expiry_date
    page.locator("section.workspace button:has-text('开始比价')").click()
    page.wait_for_selector("section.result .rec-card-primary", timeout=15000)
    # missing warning 应该在主推荐卡片中显示
    warning = page.locator(".missing-warning")
    assert warning.count() >= 1
