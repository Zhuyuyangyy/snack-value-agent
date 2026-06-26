"""OCR orchestrator 测试。"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_ocr_result_dataclass():
    """OCRResult 数据结构正确。"""
    from backend.extractor import OCRResult

    r = OCRResult(
        raw_text="到手价19.9",
        backend_used="LocalRapidOCR",
        elapsed_ms=812.5,
    )
    assert r.raw_text == "到手价19.9"
    assert r.backend_used == "LocalRapidOCR"
    assert r.elapsed_ms == 812.5
    assert r.warnings == []


def test_ocr_result_with_warnings():
    """OCRResult 可携带 warnings。"""
    from backend.extractor import OCRResult

    r = OCRResult(
        raw_text="",
        backend_used="LocalRapidOCR",
        elapsed_ms=100.0,
        warnings=["Cloud timeout", "Fallback"],
    )
    assert len(r.warnings) == 2
    assert r.warnings == ["Cloud timeout", "Fallback"]


@pytest.mark.asyncio
async def test_local_rapid_ocr_decodes_and_calls_engine(monkeypatch):
    """LocalRapidOCR 用 cv2 解码并调用 RapidOCR 引擎。"""
    from backend.extractor import LocalRapidOCR

    fake_engine_calls = []

    def fake_engine_call(img):
        fake_engine_calls.append(img)
        return (
            [[None, "到手价19.9", None], [None, "净含量84g", None]],
            100.0,
        )

    class FakeRapid:
        def __init__(self):
            pass
        def __call__(self, img):
            return fake_engine_call(img)

    fake_cv2 = MagicMock()
    fake_cv2.imdecode.return_value = "fake_img_array"

    monkeypatch.setitem(sys.modules, "rapidocr", MagicMock(RapidOCR=FakeRapid))
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    sem = asyncio.Semaphore(1)
    backend = LocalRapidOCR(sem)

    result = await backend.ocr(b"\x89PNG\r\n\x1a\n fake bytes")

    assert result.raw_text == "到手价19.9\n净含量84g"
    assert result.backend_used == "LocalRapidOCR"
    assert result.elapsed_ms >= 0
    assert fake_cv2.imdecode.called
    assert len(fake_engine_calls) == 1


@pytest.mark.asyncio
async def test_cloud_minimax_returns_empty_raises(monkeypatch):
    """CloudMinimaxOCR 返回空文本时抛 RuntimeError（触发回退）。"""
    from backend.extractor import CloudMinimaxOCR

    async def fake_ocr(b):
        return ""

    monkeypatch.setattr("backend.extractor.ocr_with_minimax", fake_ocr)

    backend = CloudMinimaxOCR()
    with pytest.raises(RuntimeError, match="empty text"):
        await backend.ocr(b"fake")


@pytest.mark.asyncio
async def test_cloud_minimax_success(monkeypatch):
    """CloudMinimaxOCR 成功时返回 OCRResult。"""
    from backend.extractor import CloudMinimaxOCR

    async def fake_ocr(b):
        return "到手价19.9\n净含量84g"

    monkeypatch.setattr("backend.extractor.ocr_with_minimax", fake_ocr)

    backend = CloudMinimaxOCR()
    result = await backend.ocr(b"fake")
    assert result.raw_text == "到手价19.9\n净含量84g"
    assert result.backend_used == "CloudMinimaxOCR"
    assert result.elapsed_ms >= 0
