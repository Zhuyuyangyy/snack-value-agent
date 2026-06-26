"""配置模块测试。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_minimax_env_defaults(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_GROUP_ID", raising=False)
    # 强制重置缓存
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
    from backend.config import MINIMAX_API_KEY, MINIMAX_GROUP_ID
    assert MINIMAX_API_KEY == ""
    assert MINIMAX_GROUP_ID == ""


def test_ocr_timeout_default(monkeypatch):
    monkeypatch.delenv("OCR_TIMEOUT_SECONDS", raising=False)
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
    from backend.config import OCR_TIMEOUT_SECONDS
    assert OCR_TIMEOUT_SECONDS == 20.0


def test_max_image_size_default(monkeypatch):
    monkeypatch.delenv("MAX_IMAGE_SIZE_BYTES", raising=False)
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
    from backend.config import MAX_IMAGE_SIZE_BYTES
    assert MAX_IMAGE_SIZE_BYTES == 10 * 1024 * 1024


def test_local_concurrency_default(monkeypatch):
    monkeypatch.delenv("LOCAL_OCR_MAX_CONCURRENCY", raising=False)
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
    from backend.config import LOCAL_OCR_MAX_CONCURRENCY
    assert LOCAL_OCR_MAX_CONCURRENCY == 1


def test_env_override(monkeypatch):
    monkeypatch.setenv("OCR_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("MAX_IMAGE_SIZE_BYTES", "2097152")
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
    from backend.config import OCR_TIMEOUT_SECONDS, MAX_IMAGE_SIZE_BYTES
    assert OCR_TIMEOUT_SECONDS == 5.0
    assert MAX_IMAGE_SIZE_BYTES == 2097152