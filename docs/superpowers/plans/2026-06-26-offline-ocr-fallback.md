# Offline OCR Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `POST /api/extract` 增加本地 RapidOCR 兜底。无 `MINIMAX_API_KEY` 时仍可识别中文零食截图；有 key 时云端失败/超时自动回退本地。

**Architecture:** 新增 `OCROrchestrator` 统一调度云端 + 本地后端（async Protocol），本地 OCR 用 `asyncio.to_thread` 包 RapidOCR 同步调用，`asyncio.Semaphore(1)` 限制并发。响应结构改为 `{ocr, fields, raw_text}` 三段式，前端同步适配。

**Tech Stack:** FastAPI + httpx（已有）+ rapidocr>=3.9.0 + onnxruntime>=1.18 + opencv-python-headless + pytest

**Spec:** [docs/superpowers/specs/2026-06-26-offline-ocr-fallback-design.md](../specs/2026-06-26-offline-ocr-fallback-design.md)

---

## File Structure

### 新增文件

| 路径 | 职责 |
|---|---|
| `backend/config.py` | OCR 相关环境变量集中配置（超时、并发、文件大小） |
| `tests/test_ocr_orchestrator.py` | 后端选择、回退、超时、并发限制 |
| `tests/test_extract_api.py` | `/api/extract` HTTP 行为（413/422/503/200） |

### 修改文件

| 路径 | 改动 |
|---|---|
| `backend/extractor.py` | 新增 `OCRResult` dataclass、`OCRBackend` 协议、`LocalRapidOCR`、`CloudMinimaxOCR`、`OCROrchestrator`；保留所有现有函数 |
| `backend/app.py` | `/api/extract` 改为 async，调用 orchestrator，统一错误码 |
| `backend/requirements.txt` | + `rapidocr>=3.9.0`、`onnxruntime>=1.18`、`opencv-python-headless>=4.8` |
| `frontend/index.html` | `extractFromImage()` 适配新响应结构，OCR 元信息展示 |

---

## Task 1: 添加配置模块

**Files:**
- Create: `backend/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
python -m pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.config'`

- [ ] **Step 3: 写实现**

```python
# backend/config.py
"""项目配置：从环境变量读取，提供默认值。"""
import os

# MiniMax 云端 OCR（可选）
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")

# OCR 兜底配置（V0.2.1 新增）
OCR_TIMEOUT_SECONDS = float(os.environ.get("OCR_TIMEOUT_SECONDS", "20"))
CLOUD_OCR_TIMEOUT_SECONDS = float(os.environ.get("CLOUD_OCR_TIMEOUT_SECONDS", "30"))
LOCAL_OCR_MAX_CONCURRENCY = int(os.environ.get("LOCAL_OCR_MAX_CONCURRENCY", "1"))
MAX_IMAGE_SIZE_BYTES = int(os.environ.get("MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024)))
```

- [ ] **Step 4: 跑测试，验证通过**

```bash
python -m pytest tests/test_config.py -v
```

Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add backend/config.py tests/test_config.py
git commit -m "feat(config): add OCR fallback configuration module"
```

---

## Task 2: 迁移现有 OCR 配置到 config 模块

**Files:**
- Modify: `backend/extractor.py:213-215`（移除 MINIMAX_API_KEY/MINIMAX_GROUP_ID 常量）
- Modify: `backend/extractor.py` 顶部 import

- [ ] **Step 1: 修改 extractor.py 顶部 import**

将 `backend/extractor.py` 顶部从：
```python
import base64
import json
import os
import re
```
改为：
```python
import base64
import json
import os
import re

from .config import (
    MINIMAX_API_KEY,
    MINIMAX_GROUP_ID,
)
```

保留 `os` import 因为其他地方可能用到。

- [ ] **Step 2: 移除 extractor.py 中的常量定义**

删除 `backend/extractor.py` 第 213-215 行：
```python
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"
```

将 `MINIMAX_BASE_URL` 改为：
```python
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"
```

保留（这是 URL 常量，不是配置）。

- [ ] **Step 3: 验证现有测试不破**

```bash
python -m pytest tests/test_extractor.py -v
```

Expected: 全部通过（说明现有逻辑没受影响）

- [ ] **Step 4: 提交**

```bash
git add backend/extractor.py
git commit -m "refactor(extractor): use config module for env vars"
```

---

## Task 3: 添加 OCRResult dataclass 和 OCRBackend 协议

**Files:**
- Modify: `backend/extractor.py`（在 `ExtractedFields` 之后插入新代码）
- Test: `tests/test_ocr_orchestrator.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_ocr_orchestrator.py
"""OCR orchestrator 测试。"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_ocr_result_dataclass -v
```

Expected: `ImportError: cannot import name 'OCRResult'`

- [ ] **Step 3: 写实现**

在 `backend/extractor.py` 的 `ExtractedFields` 类定义之后（搜索 `# ---------------------------------------------------------------------- #` 后第二个分隔符），添加：

```python
# ---------------------------------------------------------------------- #
# V0.2.1 OCR 抽象层（Protocol + Result）
# ---------------------------------------------------------------------- #
@dataclass
class OCRResult:
    """单个 OCR 后端的识别结果。

    Attributes:
        raw_text: OCR 识别出的纯文本（多行用 \\n 分隔）
        backend_used: 后端类名，如 "LocalRapidOCR" / "CloudMinimaxOCR"
        elapsed_ms: 本后端实际耗时
        warnings: 此前尝试过的后端失败信息（由 orchestrator 合并填充）
    """
    raw_text: str
    backend_used: str
    elapsed_ms: float
    warnings: list[str] = field(default_factory=list)


class OCRBackend(Protocol):
    """OCR 后端协议。"""
    name: str

    async def ocr(self, image_bytes: bytes) -> OCRResult:
        """异步识别图片，返回 OCRResult。失败时抛 Exception。"""
        ...
```

- [ ] **Step 4: 跑测试，验证通过**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_ocr_result_dataclass tests/test_ocr_orchestrator.py::test_ocr_result_with_warnings -v
```

Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add backend/extractor.py tests/test_ocr_orchestrator.py
git commit -m "feat(extractor): add OCRResult dataclass and OCRBackend protocol"
```

---

## Task 4: 实现 LocalRapidOCR 后端

**Files:**
- Modify: `backend/extractor.py`（在 `OCRBackend` 协议定义之后插入 `LocalRapidOCR` 类）
- Test: `tests/test_ocr_orchestrator.py`

- [ ] **Step 1: 写失败的测试**

在 `tests/test_ocr_orchestrator.py` 末尾添加：

```python
@pytest.mark.asyncio
async def test_local_rapid_ocr_decodes_and_calls_engine(monkeypatch):
    """LocalRapidOCR 用 cv2 解码并调用 RapidOCR 引擎。"""
    from backend.extractor import LocalRapidOCR

    fake_engine = MagicMock()
    fake_engine.return_value = (
        [[None, "到手价19.9", None], [None, "净含量84g", None]],
        100.0,
    )

    class FakeRapid:
        def __init__(self):
            pass
        def __call__(self, img):
            return fake_engine(img)

    monkeypatch.setitem(sys.modules, "rapidocr", MagicMock(RapidOCR=FakeRapid))
    monkeypatch.setitem(sys.modules, "cv2", MagicMock())

    # mock cv2.imdecode 返回非 None
    sys.modules["cv2"].imdecode.return_value = "fake_img"

    sem = asyncio.Semaphore(1)
    backend = LocalRapidOCR(sem)

    result = await backend.ocr(b"\x89PNG\r\n\x1a\n fake")

    assert result.raw_text == "到手价19.9\n净含量84g"
    assert result.backend_used == "LocalRapidOCR"
    assert result.elapsed_ms >= 0
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_local_rapid_ocr_decodes_and_calls_engine -v
```

Expected: `ImportError: cannot import name 'LocalRapidOCR'`

- [ ] **Step 3: 写实现**

在 `OCRBackend` 协议定义之后插入：

```python
class LocalRapidOCR:
    """本地 RapidOCR 后端。

    首次实例化时延迟导入 rapidocr，避免无依赖时影响其他模块。
    """
    name = "LocalRapidOCR"

    def __init__(self, semaphore: "asyncio.Semaphore"):
        try:
            from rapidocr import RapidOCR
        except ImportError as e:
            raise RuntimeError(
                "rapidocr 未安装，请运行: pip install 'rapidocr>=3.9.0' onnxruntime opencv-python-headless"
            ) from e
        self._engine = RapidOCR()
        self._sem = semaphore

    async def ocr(self, image_bytes: bytes) -> OCRResult:
        import asyncio
        import time

        async with self._sem:
            start = time.monotonic()
            try:
                text = await asyncio.wait_for(
                    asyncio.to_thread(self._sync_ocr, image_bytes),
                    timeout=__import__("backend.config", fromlist=["OCR_TIMEOUT_SECONDS"]).OCR_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"LocalRapidOCR timeout after "
                    f"{__import__('backend.config', fromlist=['OCR_TIMEOUT_SECONDS']).OCR_TIMEOUT_SECONDS}s"
                )
        return OCRResult(
            raw_text=text,
            backend_used=self.name,
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    def _sync_ocr(self, image_bytes: bytes) -> str:
        import cv2
        import numpy as np

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("LocalRapidOCR: image decode failed (unsupported format?)")
        result, _elapse = self._engine(img)
        if not result:
            return ""
        return "\n".join(str(line[1]) for line in result)
```

为避免循环 import 麻烦，使用 `__import__("backend.config", ...)` 延迟读取 `OCR_TIMEOUT_SECONDS`。或者更好的做法：在模块顶部添加 `from .config import OCR_TIMEOUT_SECONDS`。**最终实现采用后者**，请将上面 `asyncio.wait_for` 的 timeout 参数改为：

```python
from .config import OCR_TIMEOUT_SECONDS
...
            text = await asyncio.wait_for(
                asyncio.to_thread(self._sync_ocr, image_bytes),
                timeout=OCR_TIMEOUT_SECONDS,
            )
```

并在测试中保持 `OCR_TIMEOUT_SECONDS` 默认值（20s）足够长，不会因测试机器慢而误超时。

- [ ] **Step 4: 跑测试，验证通过**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_local_rapid_ocr_decodes_and_calls_engine -v
```

Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add backend/extractor.py tests/test_ocr_orchestrator.py
git commit -m "feat(extractor): add LocalRapidOCR backend with cv2 decode"
```

---

## Task 5: 实现 CloudMinimaxOCR 后端

**Files:**
- Modify: `backend/extractor.py`（在 `LocalRapidOCR` 之后插入 `CloudMinimaxOCR` 类）
- Test: `tests/test_ocr_orchestrator.py`

- [ ] **Step 1: 写失败的测试**

```python
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
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_cloud_minimax_returns_empty_raises -v
```

Expected: `ImportError: cannot import name 'CloudMinimaxOCR'`

- [ ] **Step 3: 写实现**

在 `LocalRapidOCR` 之后插入：

```python
class CloudMinimaxOCR:
    """云端 MiniMax Vision OCR 后端。

    包装现有 `ocr_with_minimax` 函数以满足 OCRBackend 协议。
    """
    name = "CloudMinimaxOCR"

    async def ocr(self, image_bytes: bytes) -> OCRResult:
        import asyncio
        import time
        from .config import CLOUD_OCR_TIMEOUT_SECONDS

        start = time.monotonic()
        try:
            text = await asyncio.wait_for(
                ocr_with_minimax(image_bytes),
                timeout=CLOUD_OCR_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"CloudMinimaxOCR timeout after {CLOUD_OCR_TIMEOUT_SECONDS}s"
            )
        if not text or not text.strip():
            raise RuntimeError("CloudMinimaxOCR returned empty text")
        return OCRResult(
            raw_text=text,
            backend_used=self.name,
            elapsed_ms=(time.monotonic() - start) * 1000,
        )
```

- [ ] **Step 4: 跑测试，验证通过**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_cloud_minimax_returns_empty_raises tests/test_ocr_orchestrator.py::test_cloud_minimax_success -v
```

Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add backend/extractor.py tests/test_ocr_orchestrator.py
git commit -m "feat(extractor): add CloudMinimaxOCR backend wrapper"
```

---

## Task 6: 实现 OCROrchestrator（后端选择 + 回退）

**Files:**
- Modify: `backend/extractor.py`（在 `CloudMinimaxOCR` 之后插入 `OCROrchestrator` 类）
- Test: `tests/test_ocr_orchestrator.py`

- [ ] **Step 1: 写失败的测试**

```python
@pytest.mark.asyncio
async def test_orchestrator_no_cloud_uses_local(monkeypatch):
    """无云端配置时直接走本地。"""
    from backend.extractor import OCROrchestrator

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.return_value = OCRResult(raw_text="ok", backend_used="LocalRapidOCR", elapsed_ms=10)

    monkeypatch.setattr("backend.extractor.LocalRapidOCR", lambda sem: fake_local)

    orch = OCROrchestrator()
    result = await orch.run(b"fake")
    assert result.backend_used == "LocalRapidOCR"
    assert fake_local.ocr.await_count == 1


@pytest.mark.asyncio
async def test_orchestrator_fallback_on_cloud_failure(monkeypatch):
    """云端失败时回退到本地。"""
    from backend.extractor import OCROrchestrator, OCRResult

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "k")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "g")

    fake_cloud = AsyncMock()
    fake_cloud.name = "CloudMinimaxOCR"
    fake_cloud.ocr.side_effect = RuntimeError("timeout")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.return_value = OCRResult(raw_text="local_ok", backend_used="LocalRapidOCR", elapsed_ms=10)

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
    from backend.extractor import OCROrchestrator, OCRResult

    monkeypatch.setattr("backend.extractor.MINIMAX_API_KEY", "k")
    monkeypatch.setattr("backend.extractor.MINIMAX_GROUP_ID", "g")

    fake_cloud = AsyncMock()
    fake_cloud.name = "CloudMinimaxOCR"
    fake_cloud.ocr.side_effect = RuntimeError("empty text")

    fake_local = AsyncMock()
    fake_local.name = "LocalRapidOCR"
    fake_local.ocr.return_value = OCRResult(raw_text="local", backend_used="LocalRapidOCR", elapsed_ms=10)

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
```

并在文件顶部添加缺失的 import：

```python
from backend.extractor import OCRResult  # 已有
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
python -m pytest tests/test_ocr_orchestrator.py::test_orchestrator_no_cloud_uses_local -v
```

Expected: `ImportError: cannot import name 'OCROrchestrator'`

- [ ] **Step 3: 写实现**

在 `CloudMinimaxOCR` 之后插入：

```python
class OCROrchestrator:
    """OCR 后端调度器：按顺序尝试，失败回退。

    优先级：
        1. CloudMinimaxOCR（仅当 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID 都配置）
        2. LocalRapidOCR（兜底，无 key 或云端失败时启用）

    本地 OCR 受 semaphore 限制并发。
    """
    def __init__(self):
        import asyncio
        from .config import (
            MINIMAX_API_KEY,
            MINIMAX_GROUP_ID,
            LOCAL_OCR_MAX_CONCURRENCY,
        )

        self._local_sem = asyncio.Semaphore(LOCAL_OCR_MAX_CONCURRENCY)
        self.backends: list = []
        if MINIMAX_API_KEY and MINIMAX_GROUP_ID:
            self.backends.append(CloudMinimaxOCR())
        # 本地总是兜底（无 key 或云端失败时启用）
        try:
            self.backends.append(LocalRapidOCR(self._local_sem))
        except RuntimeError:
            if not self.backends:
                raise

    async def run(self, image_bytes: bytes) -> OCRResult:
        from .config import MAX_IMAGE_SIZE_BYTES

        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"image too large: {len(image_bytes)} > {MAX_IMAGE_SIZE_BYTES}"
            )

        warnings: list[str] = []
        last_err: Exception | None = None

        for backend in self.backends:
            try:
                result = await backend.ocr(image_bytes)
                result.warnings = warnings + result.warnings
                return result
            except Exception as e:
                msg = f"{backend.name} failed: {e}"
                warnings.append(msg)
                last_err = e

        raise RuntimeError(
            f"所有 OCR 后端失败: {' | '.join(warnings)}"
        ) from last_err
```

- [ ] **Step 4: 跑测试，验证通过**

```bash
python -m pytest tests/test_ocr_orchestrator.py -v
```

Expected: 全部 orchestrator 测试通过（5 个新测试 + 之前的 LocalRapidOCR / CloudMinimaxOCR 测试）

- [ ] **Step 5: 提交**

```bash
git add backend/extractor.py tests/test_ocr_orchestrator.py
git commit -m "feat(extractor): add OCROrchestrator with fallback"
```

---

## Task 7: 改造 /api/extract 路由

**Files:**
- Modify: `backend/app.py:184-202`（`/api/extract` 路由）
- Test: `tests/test_extract_api.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_extract_api.py
"""/api/extract HTTP 行为测试。"""
import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client():
    from backend.app import app
    return TestClient(app)


def test_extract_empty_file_returns_422(client):
    """上传空文件返回 422。"""
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 422


def test_extract_oversized_returns_413(client, monkeypatch):
    """上传超大图片返回 413，且不进入 OCR。"""
    from backend.extractor import OCROrchestrator
    fake_run = __import__("asyncio").coroutine(lambda b: None)  # 不应被调用
    monkeypatch.setattr(OCROrchestrator, "run", fake_run)

    from backend.config import MAX_IMAGE_SIZE_BYTES
    files = {"file": ("big.jpg", io.BytesIO(b"x" * (MAX_IMAGE_SIZE_BYTES + 1)), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 413


def test_extract_no_backend_returns_503(client, monkeypatch):
    """无 OCR 后端时返回 503（不是 500）。"""
    from backend.extractor import OCROrchestrator

    async def fake_run(b):
        raise RuntimeError("无 OCR 后端可用：请安装 rapidocr 或配置 MINIMAX_API_KEY")

    monkeypatch.setattr(OCROrchestrator, "run", fake_run)

    files = {"file": ("x.jpg", io.BytesIO(b"fake"), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 503
    assert "手动粘贴" in res.json()["detail"] or "OCR" in res.json()["detail"]


def test_extract_success_returns_three_part_response(client, monkeypatch):
    """成功响应包含 ocr / fields / raw_text 三段。"""
    from backend.extractor import OCROrchestrator, OCRResult

    async def fake_run(b):
        return OCRResult(
            raw_text="到手价19.9\n净含量84g",
            backend_used="LocalRapidOCR",
            elapsed_ms=812.0,
        )

    monkeypatch.setattr(OCROrchestrator, "run", fake_run)

    files = {"file": ("x.jpg", io.BytesIO(b"fake"), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 200
    body = res.json()
    assert "ocr" in body
    assert "fields" in body
    assert "raw_text" in body
    assert body["ocr"]["backend_used"] == "LocalRapidOCR"
    assert body["ocr"]["elapsed_ms"] == 812.0
    assert body["fields"]["total_price"]["value"] == "19.90"
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
python -m pytest tests/test_extract_api.py::test_extract_empty_file_returns_422 -v
```

Expected: 状态码错误（当前是 422 但 detail 不同，或 200）

- [ ] **Step 3: 改造 /api/extract**

将 `backend/app.py` 第 184-202 行（`/api/extract` 路由）替换为：

```python
@app.post("/api/extract")
async def extract_from_screenshot(file: UploadFile = File(...)):
    """上传商品截图 → OCR → 正则/规则提取 → 返回候选字段 + OCR 元信息。

    OCR 顺序：云端 MiniMax（如果有 key） → 本地 RapidOCR（兜底）。

    Returns:
        200: {ocr: {backend_used, elapsed_ms, warnings}, fields: {...}, raw_text: "..."}
        413: 图片过大
        422: 上传文件为空
        503: 所有 OCR 后端不可用
        500: 未预期异常
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="上传文件为空")

    from .extractor import OCROrchestrator
    from .config import MAX_IMAGE_SIZE_BYTES

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"图片过大（{len(image_bytes)} > {MAX_IMAGE_SIZE_BYTES} 字节），请压缩后重试",
        )

    try:
        orchestrator = OCROrchestrator()
        ocr_result = await orchestrator.run(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except RuntimeError as e:
        # 所有 OCR 后端失败或无后端可用
        detail = str(e)
        if "无 OCR 后端" in detail or "rapidocr" in detail.lower():
            detail = "OCR 暂不可用：请 `pip install 'rapidocr>=3.9.0' onnxruntime opencv-python-headless` 或配置 MINIMAX_API_KEY"
        else:
            detail = f"OCR 暂时不可用：{detail}。请稍后重试或手动粘贴文本。"
        raise HTTPException(status_code=503, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 处理失败: {e}")

    fields = extract_fields_from_text(ocr_result.raw_text)
    return {
        "ocr": {
            "backend_used": ocr_result.backend_used,
            "elapsed_ms": round(ocr_result.elapsed_ms, 1),
            "warnings": ocr_result.warnings,
        },
        "fields": extracted_to_dict(fields),
        "raw_text": ocr_result.raw_text,
    }
```

注意：`extracted_to_dict(fields)` 当前返回的是 `{"total_price": {...}, ...}`，**而新的响应希望是 `fields` 包装一层**。所以应该修改为：

```python
        "fields": extracted_to_dict(fields),
        "raw_text": ocr_result.raw_text,
```

`extracted_to_dict` 已经是 `{total_price: {...}, ...}` 形状，与 `fields` 键的预期一致。

- [ ] **Step 4: 跑测试，验证通过**

```bash
python -m pytest tests/test_extract_api.py -v
```

Expected: 4 passed

- [ ] **Step 5: 跑全部测试，确保没破**

```bash
python -m pytest tests/ -v
```

Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add backend/app.py tests/test_extract_api.py
git commit -m "feat(api): /api/extract returns ocr+fields+raw_text with proper HTTP codes"
```

---

## Task 8: 更新 requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 添加依赖**

将 `backend/requirements.txt` 改为：

```txt
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.5
httpx>=0.27
python-multipart>=0.0.6
rapidocr>=3.9.0
onnxruntime>=1.18
opencv-python-headless>=4.8
```

- [ ] **Step 2: 验证 import 不报错（不实际安装大包）**

```bash
python -c "from backend.extractor import LocalRapidOCR; print('import path OK')"
```

Expected: `import path OK`（实际类不会实例化因为没装 rapidocr，但 import 路径通畅）

- [ ] **Step 3: 提交**

```bash
git add backend/requirements.txt
git commit -m "chore(deps): add rapidocr, onnxruntime, opencv-python-headless"
```

---

## Task 9: 适配前端响应结构

**Files:**
- Modify: `frontend/index.html:388-403`（`extractFromImage` 函数）
- Modify: `frontend/index.html:472`（`renderConfirmCard` 函数读取字段位置）

- [ ] **Step 1: 改 extractFromImage 处理新响应**

将 `frontend/index.html` 第 388-403 行（`extractFromImage` 函数）替换为：

```javascript
async function extractFromImage(file){
  const area = document.getElementById('confirmArea');
  area.style.display = 'block';
  area.innerHTML = '<div class="skeleton">正在识别截图中的商品信息…</div>';
  const fd = new FormData();
  fd.append('file', file);
  try{
    const res = await fetch('/api/extract',{method:'POST',body:fd});
    if(!res.ok){
      const e = await res.json().catch(()=>({}));
      const code = res.status;
      let hint = '';
      if(code === 503) hint = '<br><span style="font-size:12px">OCR 暂不可用，请尝试手动粘贴 OCR 文本</span>';
      else if(code === 413) hint = '<br><span style="font-size:12px">图片过大，请压缩到 10MB 以下</span>';
      else if(code === 422) hint = '<br><span style="font-size:12px">上传文件为空</span>';
      throw new Error((e.detail || '识别失败') + hint);
    }
    const data = await res.json();
    // 兼容旧结构（fields 已是 dict）+ 新增 ocr 元信息
    extractedData = {
      ...data.fields,
      _ocr: data.ocr,
      _raw_text: data.raw_text,
    };
    renderConfirmCard(extractedData, data.ocr, data.raw_text);
  }catch(err){
    area.innerHTML = `<div class="empty-hint" style="color:var(--bad)">识别失败：${err.message}</div>`;
  }
}
```

- [ ] **Step 2: 改 renderConfirmCard 接受 ocr 元信息**

查找 `renderConfirmCard` 函数（大约 472 行附近），其签名从 `function renderConfirmCard(data)` 改为：

```javascript
function renderConfirmCard(data, ocrMeta, rawText){
  // data: 字段字典 {total_price, total_weight_g, ...}
  // ocrMeta: {backend_used, elapsed_ms, warnings}
  // rawText: OCR 原文
  ...
}
```

并在卡片头部（`<details>` 之前）添加 OCR 元信息展示：

```javascript
  if(ocrMeta){
    let warnHtml = '';
    if(ocrMeta.warnings && ocrMeta.warnings.length){
      warnHtml = `<div style="font-size:11px;color:var(--warn);margin-top:4px">⚠️ ${ocrMeta.warnings.join('；')}</div>`;
    }
    const backendLabel = ocrMeta.backend_used === 'LocalRapidOCR' ? '本地 OCR' : '云端 OCR';
    const fallbackHint = ocrMeta.warnings && ocrMeta.warnings.length ? '（已自动回退）' : '';
    html = `<div style="font-size:11px;color:var(--text-dim);margin-bottom:8px">识别来源：${backendLabel}${fallbackHint} · 耗时 ${Math.round(ocrMeta.elapsed_ms)}ms</div>${warnHtml}` + html;
  }
```

- [ ] **Step 3: 在 extractFromText 中也同步处理**

将 `extractFromText` 函数（约 410 行）末尾的 `renderConfirmCard(data)` 改为：

```javascript
    // 文本提取不经过 OCR，但保留兼容
    extractedData = data;
    renderConfirmCard(data, null, text);
```

- [ ] **Step 4: 手动验证前端**

启动服务：
```bash
cd "D:\ZYY Project\Evalution price agent"
uvicorn backend.app:app --reload --port 8000
```

打开浏览器 http://localhost:8000，上传一张零食截图，确认：
- 卡片头部显示"识别来源：本地/云端 OCR · 耗时 Xms"
- 如有回退，显示"已自动回退" + warning 文本

- [ ] **Step 5: 提交**

```bash
git add frontend/index.html
git commit -m "feat(frontend): show OCR backend + warnings in confirm card"
```

---

## Task 10: 更新 README

**Files:**
- Modify: `README.md`（如果不存在则创建）

- [ ] **Step 1: 添加 OCR 配置段落**

如果 README 不存在，创建 `README.md`：

```markdown
# SnackValue Agent

临期零食智能比价助手。V0.2 支持上传商品截图自动识别字段。

## 启动

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

打开 http://localhost:8000

## OCR 后端

`POST /api/extract` 支持两种 OCR 后端，按顺序自动选择：

1. **云端 MiniMax Vision**（如配置 `MINIMAX_API_KEY` 和 `MINIMAX_GROUP_ID` 环境变量）
2. **本地 RapidOCR**（兜底，首次启动自动下载 ~10MB 模型到 `~/.rapidocr/`）

未配置 API Key 时直接使用本地 OCR，云端失败/超时自动回退。

### 配置环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | 空 | 启用云端 OCR |
| `MINIMAX_GROUP_ID` | 空 | 启用云端 OCR |
| `OCR_TIMEOUT_SECONDS` | 20 | 本地 OCR 超时 |
| `CLOUD_OCR_TIMEOUT_SECONDS` | 30 | 云端 OCR 超时 |
| `LOCAL_OCR_MAX_CONCURRENCY` | 1 | 本地 OCR 并发上限 |
| `MAX_IMAGE_SIZE_BYTES` | 10485760 | 上传图片大小上限（10MB） |

## 响应格式

`POST /api/extract` 返回：

```json
{
  "ocr": {"backend_used": "LocalRapidOCR", "elapsed_ms": 812, "warnings": []},
  "fields": {"total_price": {"value": "19.90", "confidence": "high"}, ...},
  "raw_text": "到手价 ¥19.9\n净含量 84g×5袋\n..."
}
```
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add OCR backend documentation"
```

---

## Task 11: 端到端冒烟测试

**Files:**
- N/A（手动验证）

- [ ] **Step 1: 安装新依赖**

```bash
pip install -r backend/requirements.txt
```

Expected: 安装成功，rapidocr + onnxruntime + opencv-python-headless 就位

- [ ] **Step 2: 启动服务**

```bash
uvicorn backend.app:app --reload --port 8000
```

Expected: 启动成功，无报错

- [ ] **Step 3: 不配置 API Key 测试本地 OCR**

在浏览器中打开 http://localhost:8000，上传一张中文零食截图。

Expected:
- 响应状态 200
- 卡片显示"识别来源：本地 OCR · 耗时 Xms"
- 字段被正确提取（价格、重量等）

- [ ] **Step 4: 测试图片过大**

上传一张 11MB+ 的图片。

Expected: 状态 413，提示"图片过大，请压缩到 10MB 以下"

- [ ] **Step 5: 跑全部测试**

```bash
python -m pytest tests/ -v
```

Expected: 全部通过

- [ ] **Step 6: 提交（如果有 changelog）**

如果本任务需要更新 CHANGELOG.md，提交：

```bash
git add CHANGELOG.md
git commit -m "chore: mark V0.2.1 OCR fallback complete"
```

否则跳过此步。

---

## Self-Review

1. **Spec coverage** — 逐节对照规范：
   - §3 组件清单：config.py / extractor.py / app.py / requirements.txt / frontend / 3 个测试文件 — Task 1/2/3/4/5/6/7/8/9 覆盖 ✓
   - §5 接口：`OCRResult` dataclass (Task 3) / `OCRBackend` Protocol (Task 3) / `LocalRapidOCR` (Task 4) / `CloudMinimaxOCR` (Task 5) / `OCROrchestrator` (Task 6) ✓
   - §6 配置：Task 1 全部环境变量 ✓
   - §7 错误码：Task 7 中 413/422/503/200/500 全部覆盖 ✓
   - §8 并发超时：Task 1 (config) + Task 6 (semaphore) ✓
   - §9 响应结构：Task 7 返回 `{ocr, fields, raw_text}` ✓
   - §10 测试：Task 3/4/5/6 (orchestrator 测试) + Task 7 (API 测试) + Task 11 (E2E) ✓
   - §11 部署：Task 8 (requirements) + Task 10 (README) ✓
   - §12 成功标准：Task 11 E2E 覆盖 ✓

2. **Placeholder scan** — 无 "TBD" / "TODO" / "类似 Task N" 引用，所有代码块完整。

3. **Type consistency** —
   - `OCRResult.warnings` 字段在 Task 3 定义为 `list[str]`，Task 6 orchestrator 合并时使用 `warnings: list[str]` ✓
   - `OCRBackend.name: str` 在 Task 3 定义为 class var，所有后端（Task 4/5）都正确实现 ✓
   - `OCROrchestrator.run(b) -> OCRResult` 在 Task 6 定义，Task 7 调用一致 ✓

4. **测试 mock 一致性** — Task 4-6 中所有测试都使用 `monkeypatch.setattr` 而非 `unittest.mock.patch`，避免副作用。LocalRapidOCR 构造接受 semaphore，测试中传入 `asyncio.Semaphore(1)` 与生产一致 ✓

无问题。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-26-offline-ocr-fallback.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?