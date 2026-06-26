"""OCR orchestrator 测试。"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.extractor import OCRResult  # noqa: E402


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
async def test_local_rapid_ocr_handles_dataclass_output(monkeypatch):
    """回归测试：rapidocr >=3.x 返回 RapidOCROutput dataclass（有 .txts 属性）。

    旧版 API 返回 (result, elapse) tuple，新版是 dataclass。
    LocalRapidOCR 必须兼容两种，否则真实环境下 503。
    """
    from backend.extractor import LocalRapidOCR

    class FakeRapidOCROutput:
        def __init__(self, txts):
            self.txts = txts

    def fake_engine_call(img):
        return FakeRapidOCROutput(["到手价19.9", "净含量84g"])

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


@pytest.mark.asyncio
async def test_orchestrator_no_cloud_uses_local(monkeypatch):
    """无云端配置时直接走本地。"""
    from backend.extractor import OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.return_value = OCRResult(
        raw_text="ok", backend_used="LocalRapidOCR", elapsed_ms=10
    )

    monkeypatch.setattr("backend.extractor.LocalRapidOCR", lambda sem: fake_local)

    orch = OCROrchestrator()
    result = await orch.run(b"fake")
    assert result.backend_used == "LocalRapidOCR"
    assert fake_local.ocr.await_count == 1


@pytest.mark.asyncio
async def test_orchestrator_fallback_on_cloud_failure(monkeypatch):
    """云端失败时回退到本地。"""
    from backend.extractor import OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "k")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "g")

    fake_cloud = AsyncMock()
    fake_cloud.name = "CloudMinimaxOCR"
    fake_cloud.ocr.side_effect = RuntimeError("timeout")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.return_value = OCRResult(
        raw_text="local_ok", backend_used="LocalRapidOCR", elapsed_ms=10
    )

    monkeypatch.setattr("backend.extractor.CloudMinimaxOCR", lambda: fake_cloud)
    monkeypatch.setattr("backend.extractor.LocalRapidOCR", lambda sem: fake_local)

    orch = OCROrchestrator()
    result = await orch.run(b"fake")
    assert result.backend_used == "LocalRapidOCR"
    assert result.raw_text == "local_ok"
    assert any("CloudMinimaxOCR" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_orchestrator_fallback_on_empty_text(monkeypatch):
    """云端返回空文本时回退本地。"""
    from backend.extractor import OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "k")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "g")

    fake_cloud = AsyncMock()
    fake_cloud.name = "CloudMinimaxOCR"
    fake_cloud.ocr.side_effect = RuntimeError("empty text")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.return_value = OCRResult(
        raw_text="local", backend_used="LocalRapidOCR", elapsed_ms=10
    )

    monkeypatch.setattr("backend.extractor.CloudMinimaxOCR", lambda: fake_cloud)
    monkeypatch.setattr("backend.extractor.LocalRapidOCR", lambda sem: fake_local)

    orch = OCROrchestrator()
    result = await orch.run(b"fake")
    assert result.backend_used == "LocalRapidOCR"


@pytest.mark.asyncio
async def test_orchestrator_all_fail_raises(monkeypatch):
    """云端和本地都失败时抛 RuntimeError。"""
    from backend.extractor import OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.side_effect = RuntimeError("decode failed")

    monkeypatch.setattr("backend.extractor.LocalRapidOCR", lambda sem: fake_local)

    orch = OCROrchestrator()
    with pytest.raises(RuntimeError, match="所有 OCR 后端失败"):
        await orch.run(b"fake")


@pytest.mark.asyncio
async def test_orchestrator_rejects_oversized(monkeypatch):
    """超过 MAX_IMAGE_SIZE_BYTES 时直接抛 ValueError。"""
    from backend.extractor import OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "")

    fake_local = AsyncMock()
    monkeypatch.setattr("backend.extractor.LocalRapidOCR", lambda sem: fake_local)

    monkeypatch.setattr("backend.extractor.MAX_IMAGE_SIZE_BYTES", 100)

    orch = OCROrchestrator()
    with pytest.raises(ValueError, match="image too large"):
        await orch.run(b"x" * 200)
    assert fake_local.ocr.await_count == 0
