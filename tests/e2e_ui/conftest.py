"""Playwright fixtures：启动 server + browser + page。

Note: 这个 fixture 自动调用 `db.init_db()` 确保测试时数据库已初始化，
避免 V0.3 迁移 + V0.2 baseline 共存的边缘情况。
"""
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
import urllib.request
from playwright.sync_api import Browser, Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_PORT = 8766  # 避免与现有 8765 冲突


def _wait_for_server(url: str, timeout: int = 15) -> bool:
    """等待 server 启动完成。"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


@pytest.fixture(scope="session")
def server_url() -> Generator[str, None, None]:
    """启动 FastAPI server 一次，session 共享。"""
    # 先初始化 DB schema（确保 V0.3 迁移生效）
    from backend.database import init_db
    init_db()

    python_exe = sys.executable
    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.app:app", "--port", str(SERVER_PORT), "--log-level", "error"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://localhost:{SERVER_PORT}"
    try:
        assert _wait_for_server(f"{url}/api/health", timeout=15), "server failed to start"
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """启动 Chromium 一次，session 共享。"""
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser, server_url: str) -> Generator[Page, None, None]:
    """每个测试一个干净的 page（desktop viewport）。"""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    p = context.new_page()
    p.goto(server_url)
    p.wait_for_load_state("networkidle")
    yield p
    context.close()
