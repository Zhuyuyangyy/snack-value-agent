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


@pytest.mark.asyncio
async def test_cloud_minimax_timeout_raises(monkeypatch):
    """CloudMinimaxOCR 超时时抛 RuntimeError（触发回退）。"""
    from backend.extractor import CloudMinimaxOCR

    # 直接测试：替换 asyncio.wait_for 为抛超时版本（不 await coro）
    async def fake_wait_for(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr("backend.extractor.ocr_with_minimax", AsyncMock())
    # monkeypatch asyncio module global since the production code does
    # `import asyncio` inside the method which resolves to the same module.
    monkeypatch.setattr("asyncio.wait_for", fake_wait_for)

    backend = CloudMinimaxOCR()
    with pytest.raises(RuntimeError, match="timeout"):
        await backend.ocr(b"fake")


@pytest.mark.asyncio
async def test_orchestrator_serializes_local_ocr(monkeypatch):
    """并发调用时，本地 OCR 通过 semaphore 串行执行。"""
    from backend.extractor import OCRResult, OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "")

    call_log = []
    call_started = asyncio.Event()
    call_can_finish = asyncio.Event()

    class FakeLocal:
        name = "LocalRapidOCR"

        def __init__(self, sem):
            # 必须接受并使用 semaphore 才能验证串行化
            self._sem = sem

        async def ocr(self, b):
            async with self._sem:
                call_log.append(("start", len(call_log)))
                call_started.set()
                await call_can_finish.wait()
                call_log.append(("end", len(call_log)))
                return OCRResult(
                    raw_text="x", backend_used="LocalRapidOCR", elapsed_ms=10
                )

    monkeypatch.setattr("backend.extractor.LocalRapidOCR", FakeLocal)

    orch = OCROrchestrator()

    # 启动 3 个并发任务
    task1 = asyncio.create_task(orch.run(b"a"))
    task2 = asyncio.create_task(orch.run(b"b"))
    task3 = asyncio.create_task(orch.run(b"c"))

    # 等第一个开始
    await call_started.wait()
    # 给其他任务一点时间尝试进入（它们应该被 semaphore 阻塞）
    await asyncio.sleep(0.05)

    # 此时应该只有 1 个 start
    starts = [c for c in call_log if c[0] == "start"]
    assert len(starts) == 1, f"semaphore 应串行化，但发现 {len(starts)} 个并发 start"

    # 释放第一个，让第二个进入
    call_can_finish.set()
    # 等所有任务完成
    results = await asyncio.gather(task1, task2, task3)
    assert all(r.backend_used == "LocalRapidOCR" for r in results)
    # 最终应有 3 个 start 和 3 个 end
    assert len(call_log) == 6
