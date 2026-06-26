"""设计 tokens 验证。"""
from playwright.sync_api import Page


def test_design_tokens_defined(page: Page):
    bg_0 = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg-0')")
    accent = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')")
    assert bg_0.strip() == "#fafaf7", f"--bg-0 应为 #fafaf7，实际 {bg_0}"
    assert accent.strip() == "#0071e3", f"--accent 应为 #0071e3，实际 {accent}"


def test_body_uses_design_font(page: Page):
    font = page.evaluate("getComputedStyle(document.body).fontFamily")
    assert "system-ui" in font or "PingFang SC" in font or "Microsoft YaHei" in font
