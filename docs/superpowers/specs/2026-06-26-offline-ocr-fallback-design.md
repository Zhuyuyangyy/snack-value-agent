# SnackValue Agent — Offline OCR Fallback Design v0.1-reviewed

- **Date**: 2026-06-26
- **Status**: Reviewed, pending user approval
- **Scope**: V0.2.1 — 本地 OCR 兜底 + 云端 OCR 回退路径
- **Reference APK**: 慢慢买.apk (Google ML Kit 中文 OCR，端侧 ~2.5MB 模型)
- **Reference plan**: docs/superpowers/specs/2026-06-26-offline-ocr-fallback-design.md (this file)

---

## 1. Goal & Scope

为 SnackValue Agent 后端增加**本地 OCR 兜底**，覆盖两种场景：

1. **未配置 `MINIMAX_API_KEY`** — `POST /api/extract` 仍然可用，不再 503。
2. **配置了云端但调用失败/超时** — 自动回退到本地，用户无感。

**不做**（V0.2.1 边界）：
- 通用文档 OCR（仅优化中文商品截图）
- 一图多商品识别
- 多语言识别（先 zh + en 足够）
- LLM 字段兜底（推迟到 V0.3）

参考 `慢慢买.apk` 的端侧 OCR 思路（ML Kit Chinese + 拉丁，TFLite ~2.5MB），在 Python 端用 RapidOCR 复现。

---

## 2. Architecture

```
┌──────────────┐    POST /api/extract    ┌─────────────┐
│  前端        │ ──────────────────────▶ │  FastAPI    │
│  index.html  │ ◀────── JSON ────────── │  app.py     │
└──────────────┘                          └──────┬──────┘
                                                 │
                                          ┌──────▼──────────┐
                                          │ OCROrchestrator │  (新增)
                                          │  - async run    │
                                          │  - 超时/并发    │
                                          │  - 失败回退     │
                                          └──────┬──────────┘
                                                 │
                          ┌──────────────────────┼──────────────────────┐
                          ▼                      ▼                      ▼
                CloudMinimaxOCR         LocalRapidOCR          (未来扩展位)
                (async httpx)        (asyncio.to_thread)
                          │                      │
                          └──── 回退 on 失败/超时 ──┘
                                                 │
                                          ┌──────▼──────────┐
                                          │ extract_fields_ │  (现有，不动)
                                          │ from_text()     │
                                          └─────────────────┘
```

---

## 3. Components

| 文件 | 改动 | 内容 |
|---|---|---|
| `backend/extractor.py` | 修改 | 新增 `OCRResult` dataclass、`OCRBackend` 协议、`LocalRapidOCR`、`CloudMinimaxOCR`、`OCROrchestrator` |
| `backend/app.py` | 修改 | `/api/extract` 改为 async，调用 orchestrator，HTTP 错误码分类 |
| `backend/requirements.txt` | 修改 | + `rapidocr>=3.9.0` + `onnxruntime>=1.18` |
| `backend/config.py` | 新增 | OCR 相关环境变量集中（超时/并发/最大尺寸） |
| `frontend/index.html` | 修改 | `/api/extract` 响应适配新结构（OCR 元信息 + fields + raw_text） |
| `tests/test_ocr_orchestrator.py` | 新增 | 后端选择、回退、空文本回退、超时回退 |
| `tests/test_extract_api.py` | 新增 | HTTP 行为（503 / 422 / 413 / 200） |
| `tests/test_extractor.py` | 保留 | 现有正则字段提取测试 |

---

## 4. Data Flow

```
image_bytes (≤10MB)
    │
    ▼
POST /api/extract (FastAPI, async)
    │
    ▼
OCROrchestrator.run(image_bytes)
    │
    ├─ 有云端配置 → CloudMinimaxOCR
    │      ├─ 成功+非空 → 返回
    │      ├─ 超时/异常/空文本 → 记录 warning，回退
    │      └─ 本地可用 → LocalRapidOCR
    │
    └─ 无云端配置 → 直接 LocalRapidOCR
           │
           ├─ _local_ocr_semaphore acquire
           ├─ asyncio.wait_for(asyncio.to_thread(...), timeout=20s)
           └─ 返回 OCRResult(raw_text, "LocalRapidOCR", elapsed_ms, warnings)
                  │
                  ▼
        extract_fields_from_text(raw_text)
                  │
                  ▼
        ExtractedFields
                  │
                  ▼
        JSON Response: { ocr, fields, raw_text }
```

---

## 5. Interface Design

### 5.1 OCRResult

```python
@dataclass
class OCRResult:
    raw_text: str
    backend_used: str
    elapsed_ms: float
    warnings: list[str] = field(default_factory=list)
```

### 5.2 OCRBackend 协议（async）

```python
from typing import Protocol

class OCRBackend(Protocol):
    name: str

    async def ocr(self, image_bytes: bytes) -> OCRResult:
        """异步 OCR，统一接口。"""
        ...
```

### 5.3 LocalRapidOCR

```python
import asyncio
import cv2
import numpy as np
from io import BytesIO  # 仅在 fallback 时使用

class LocalRapidOCR:
    name = "LocalRapidOCR"

    def __init__(self, semaphore: asyncio.Semaphore):
        from rapidocr import RapidOCR  # 延迟导入，便于无依赖时给出 503
        self._engine = RapidOCR()
        self._sem = semaphore

    async def ocr(self, image_bytes: bytes) -> OCRResult:
        async with self._sem:
            start = time.monotonic()
            try:
                text = await asyncio.wait_for(
                    asyncio.to_thread(self._sync_ocr, image_bytes),
                    timeout=OCR_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(f"LocalRapidOCR timeout after {OCR_TIMEOUT_SECONDS}s")
        return OCRResult(
            raw_text=text,
            backend_used=self.name,
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    def _sync_ocr(self, image_bytes: bytes) -> str:
        # 用 OpenCV 解码，避免依赖 Pillow
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("LocalRapidOCR: image decode failed")
        result, _elapse = self._engine(img)
        if not result:
            return ""
        return "\n".join(line[1] for line in result)
```

### 5.4 CloudMinimaxOCR

```python
class CloudMinimaxOCR:
    name = "CloudMinimaxOCR"

    async def ocr(self, image_bytes: bytes) -> OCRResult:
        start = time.monotonic()
        try:
            text = await asyncio.wait_for(
                ocr_with_minimax(image_bytes),
                timeout=CLOUD_OCR_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"CloudMinimaxOCR timeout after {CLOUD_OCR_TIMEOUT_SECONDS}s")
        if not text.strip():
            raise RuntimeError("CloudMinimaxOCR returned empty text")
        return OCRResult(
            raw_text=text,
            backend_used=self.name,
            elapsed_ms=(time.monotonic() - start) * 1000,
        )
```

### 5.5 OCROrchestrator

```python
class OCROrchestrator:
    def __init__(self):
        self.backends: list[OCRBackend] = []
        self._local_sem = asyncio.Semaphore(LOCAL_OCR_MAX_CONCURRENCY)
        if MINIMAX_API_KEY and MINIMAX_GROUP_ID:
            self.backends.append(CloudMinimaxOCR())
        # 本地总是兜底（无 key 或云端失败）
        try:
            self.backends.append(LocalRapidOCR(self._local_sem))
        except ImportError:
            # rapidocr 未安装：如果已有云端，仍可工作；否则 raise
            if not self.backends:
                raise RuntimeError(
                    "无 OCR 后端可用：请安装 rapidocr 或配置 MINIMAX_API_KEY"
                )

    async def run(self, image_bytes: bytes) -> OCRResult:
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(f"image too large: {len(image_bytes)} > {MAX_IMAGE_SIZE_BYTES}")

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

        raise RuntimeError(f"所有 OCR 后端失败: {' | '.join(warnings)}") from last_err
```

---

## 6. Configuration (`backend/config.py`)

```python
import os

# 现有
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")

# 新增 OCR 兜底配置
OCR_TIMEOUT_SECONDS = float(os.environ.get("OCR_TIMEOUT_SECONDS", "20"))
CLOUD_OCR_TIMEOUT_SECONDS = float(os.environ.get("CLOUD_OCR_TIMEOUT_SECONDS", "30"))
LOCAL_OCR_MAX_CONCURRENCY = int(os.environ.get("LOCAL_OCR_MAX_CONCURRENCY", "1"))
MAX_IMAGE_SIZE_BYTES = int(os.environ.get("MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024)))
```

---

## 7. Error Handling

| 场景 | HTTP | detail |
|---|---|---|
| 上传文件为空 | 422 | "上传文件为空" |
| 图片超过 `MAX_IMAGE_SIZE_BYTES` | 413 | "图片过大，请压缩到 10MB 以下" |
| RapidOCR 未装 + 无云端配置 | 503 | "OCR 暂不可用，请安装 rapidocr 或配置 MINIMAX_API_KEY" |
| 所有 OCR 后端均失败 | 503 | "OCR 暂时不可用，请稍后重试或手动粘贴文本" + 触发 warning |
| OCR 成功但字段提取为空 | 200 | 返回低置信度结果，前端展示手动确认卡片 |
| 未预期异常 | 500 | "OCR 处理失败: <msg>" |

**关键修正**：RapidOCR 未安装 = **503**（服务不可用），不是 500（代码崩溃）。

---

## 8. Concurrency & Timeout

| 项 | 值 | 理由 |
|---|---|---|
| `OCR_TIMEOUT_SECONDS` | 20 | 本地 CPU 推理，单张图上限 |
| `CLOUD_OCR_TIMEOUT_SECONDS` | 30 | httpx 现有 30s，提升 |
| `LOCAL_OCR_MAX_CONCURRENCY` | 1 | CPU 密集型，串行避免抢占 |
| `MAX_IMAGE_SIZE_BYTES` | 10MB | FastAPI 默认 1MB 太小，零食截图普遍 2-5MB |

本地 OCR 串行通过 `asyncio.Semaphore(1)` 实现，超时通过 `asyncio.wait_for` 实现。Semaphore 与 timeout 解耦：超时只计时实际推理时间，不计排队时间。

---

## 9. API Response Shape

`POST /api/extract` 返回结构变更（破坏性，**前端需同步更新**）：

```json
{
  "ocr": {
    "backend_used": "LocalRapidOCR",
    "elapsed_ms": 812,
    "warnings": ["CloudMinimaxOCR failed: timeout after 30s, fallback to LocalRapidOCR"]
  },
  "fields": {
    "total_price": {"value": "19.90", "confidence": "high", "source": "到手价19.9"},
    "total_weight_g": {"value": "420", "confidence": "high", "source": "84g×5袋"},
    "flavor_type": {"value": "fixed", "confidence": "medium", "source": "固定口味"},
    "flavor_name": {"value": "草莓味", "confidence": "low", "source": "口味：草莓味"},
    "expiry_date": {"value": "2026-09-01", "confidence": "high", "source": "保质期至2026.09.01"},
    "quantity": {"value": "5", "confidence": "medium", "source": "×5袋"},
    "package_type": {"value": "bag", "confidence": "medium", "source": "袋"}
  },
  "raw_text": "到手价 ¥19.9\n净含量 84g×5袋\n固定口味 草莓味\n保质期至 2026.09.01"
}
```

前端 `renderConfirmCard` 改为读取 `data.fields.*` 而非 `data.total_price` 等扁平字段。OCR 元信息展示在卡片顶部（"识别来源：本地 OCR · 耗时 812ms · 已自动回退"）。

---

## 10. Testing Strategy

### 10.1 测试文件拆分

| 文件 | 范围 |
|---|---|
| `tests/test_ocr_orchestrator.py` | 后端选择顺序、回退触发、空文本回退、超时回退、并发限制 |
| `tests/test_extract_api.py` | `/api/extract` HTTP 行为（413/422/503/200） |
| `tests/test_extractor.py` | 现有正则字段提取测试（保留不动） |

### 10.2 必须覆盖的测试用例

**test_ocr_orchestrator.py**:
1. 有云端配置 + 云端成功 → 返回云端结果，无 warnings
2. 有云端配置 + 云端抛异常 → 回退本地，返回本地结果 + warning
3. 有云端配置 + 云端返回空文本 → 回退本地
4. 有云端配置 + 云端超时（`asyncio.TimeoutError`） → 回退本地
5. 无云端配置 + 本地成功 → 直接返回本地
6. 无云端配置 + rapidocr 未装 → orchestrator 构造时抛 RuntimeError
7. 并发限制：`asyncio.gather(*[run() for _ in range(5)])` 中，本地 OCR 同时只跑 1 个

**test_extract_api.py**:
1. 上传空文件 → 422
2. 上传 > 10MB 文件 → 413，**不进入 OCR 流程**（用 mock 验证 orchestrator 未被调用）
3. rapidocr 未装 + 无云端 → 503
4. 正常上传 → 200 + 返回 `{ocr, fields, raw_text}` 结构
5. 所有后端失败 → 503 + detail 含"手动粘贴文本"提示

**test_extractor.py**（已有）:
- 价格/重量/数量/日期/口味/包装的正则提取测试，不变。

### 10.3 手动验证

启动服务后，用 30~50 张真实零食截图（来自淘宝/京东/拼多多/线下超市小票）跑 `/api/extract`，目测识别结果。

---

## 11. Configuration & Deployment

### 11.1 依赖变更

`backend/requirements.txt`：
```txt
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.5
httpx>=0.27
python-multipart>=0.0.6
rapidocr>=3.9.0
onnxruntime>=1.18
```

> 选 `rapidocr` 而非 `rapidocr-onnxruntime`：后者最新停在 1.4.4，要求 Python `<3.13`，与项目 Python 3.12/3.13 环境不兼容。`rapidocr>=3.9.0` 支持 Python 3.8~3.13。

### 11.2 模型下载

RapidOCR 首次运行自动从 PyPI 镜像下载模型到 `~/.rapidocr/`，约 10MB（detection + recognition + cls）。后续完全离线。

### 11.3 环境变量（可选）

| 变量 | 默认 | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | 空 | 有则启用云端 OCR |
| `MINIMAX_GROUP_ID` | 空 | 有则启用云端 OCR |
| `OCR_TIMEOUT_SECONDS` | 20 | 本地 OCR 超时 |
| `CLOUD_OCR_TIMEOUT_SECONDS` | 30 | 云端 OCR 超时 |
| `LOCAL_OCR_MAX_CONCURRENCY` | 1 | 本地 OCR 并发上限 |
| `MAX_IMAGE_SIZE_BYTES` | 10485760 | 上传图片大小上限 |

### 11.4 README 更新

新增段落：

```markdown
## OCR 后端

- **未配置 API Key**：使用本地 RapidOCR（首次启动自动下载 ~10MB 模型到 ~/.rapidocr/）
- **已配置 API Key**：优先使用云端 OCR，失败自动回退本地
- **响应字段**：`ocr.backend_used`、`ocr.elapsed_ms`、`ocr.warnings` 标识识别来源
```

---

## 12. Success Criteria

### 12.1 功能验收

- [ ] 无 `MINIMAX_API_KEY` 时，`POST /api/extract` 仍可识别中文零食截图
- [ ] 有 API Key 时，云端失败/超时/空文本均可自动回退到本地
- [ ] 上传 11MB 图片直接返回 413，不进入 OCR
- [ ] rapidocr 未装 + 无云端配置时，干净返回 503（不 500）
- [ ] 前端展示 OCR 来源 + 耗时 + 回退提示

### 12.2 准确度验收（自建回归集）

**测试集**：自建 30~50 张真实中文零食截图，覆盖：
- 淘宝/京东/拼多多 详情页
- 线下超市小票（可选）
- 不同字体/排版/压缩质量

**指标**：
- `required_field_accuracy` = (total_price + total_weight_g + flavor_type 三项均正确) / 总样本数
- 目标：**≥ 90%**

- `optional_field_accuracy` = (expiry_date + quantity + package_type + flavor_name) 正确率
- 目标：**≥ 70%**（口味名称本就低置信，作为参考）

> 不声称"行业基线 ≥90%"——准确度依赖具体截图质量、字体、平台、压缩程度，必须基于自建集评估。

### 12.3 性能验收

- 单张 1080p 中文零食截图，本地 OCR 端到端 ≤ 5s（P95）
- 并发 5 个请求时，本地 OCR 串行执行，平均延迟不超过 25s

---

## 13. Risks & Mitigations

| 风险 | 影响 | 缓解 |
|---|---|---|
| RapidOCR 模型下载失败（首次） | 本地 OCR 不可用 | 检测 `ImportError`，引导用户配置云端 key 或重新 `pip install` |
| 中文倾斜/竖排文字识别差 | 部分商品截图识别失败 | V0.3 引入 LLM 兜底 |
| 本地 OCR 拖慢响应 | 用户体验下降 | semaphore=1 + 20s 超时；失败立即回退 |
| 模型误识别"到手价 ¥19.9"成"到手价 ¥199" | 价格错误 | 现有正则已含范围校验 + 用户确认卡片 |
| 前端响应结构破坏性变更 | 前端报错 | 同步更新 `renderConfirmCard` 与 `extractFromImage` |

---

## 14. Future Roadmap

- **V0.2.1**（本设计）：本地 OCR 兜底 + 云端回退
- **V0.2.2**：字段确认页增强（手动纠错、复制 OCR 原文）
- **V0.2.3**：30~50 张回归集 + 准确度自动化评估
- **V0.3**：LLM 字段修复/解释增强（用户确认前自动补全口味名、纠错价格）
- **V0.4**：一图多商品识别（购物车/搜索结果页）