"""字段提取器：OCR 文本 → 正则/规则双层提取 → 结构化候选字段 + 置信度。

提取策略：
  价格/重量/数量/日期 → 正则优先（高置信）
  随机口味/指定口味   → 关键词规则（中置信）
  口味名称/包装类型   → 规则 + LLM 辅助（低→中置信）
"""
from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Literal, Protocol

import httpx

from .config import MINIMAX_API_KEY, MINIMAX_GROUP_ID, MAX_IMAGE_SIZE_BYTES, LOCAL_OCR_MAX_CONCURRENCY

# ---------------------------------------------------------------------- #
# 数据结构
# ---------------------------------------------------------------------- #
Confidence = Literal["high", "medium", "low"]


@dataclass
class FieldCandidate:
    """单个字段的提取结果。"""
    value: Optional[str] = None
    confidence: Confidence = "low"
    source: str = ""  # 匹配到的原始文本片段


@dataclass
class ExtractedFields:
    """一张截图的完整提取结果。"""
    total_price: FieldCandidate = field(default_factory=FieldCandidate)
    total_weight_g: FieldCandidate = field(default_factory=FieldCandidate)
    flavor_type: FieldCandidate = field(default_factory=FieldCandidate)
    flavor_name: FieldCandidate = field(default_factory=FieldCandidate)
    expiry_date: FieldCandidate = field(default_factory=FieldCandidate)
    quantity: FieldCandidate = field(default_factory=FieldCandidate)
    package_type: FieldCandidate = field(default_factory=FieldCandidate)
    raw_text: str = ""


# ---------------------------------------------------------------------- #
# V0.2.1 OCR 抽象层（Protocol + Result）
# ---------------------------------------------------------------------- #
@dataclass
class OCRResult:
    """单个 OCR 后端的识别结果。

    Attributes:
        raw_text: OCR 识别出的纯文本（多行用 \\n 分隔）
        backend_used: 后端类名，如 "LocalRapidOCR" / "CloudMinimaxOCR"
        elapsed_ms: 本后端实际耗时（毫秒）
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


# ---------------------------------------------------------------------- #
# V0.2.1 本地 RapidOCR 后端
# ---------------------------------------------------------------------- #
class LocalRapidOCR:
    """本地 RapidOCR 后端。

    首次实例化时延迟导入 rapidocr，避免无依赖时影响其他模块。
    使用 cv2 解码图片避免 Pillow 依赖，CPU 密集工作通过 asyncio.to_thread 调度。
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

        from .config import OCR_TIMEOUT_SECONDS

        async with self._sem:
            start = time.monotonic()
            try:
                text = await asyncio.wait_for(
                    asyncio.to_thread(self._sync_ocr, image_bytes),
                    timeout=OCR_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"LocalRapidOCR timeout after {OCR_TIMEOUT_SECONDS}s"
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
        output = self._engine(img)
        # rapidocr >=3.x 返回 RapidOCROutput dataclass（img/boxes/txts/scores/...）
        # 旧版返回 (result, elapse) tuple，需要同时兼容两种 API
        if hasattr(output, "txts"):
            txts = output.txts or []
        else:
            result = output[0] if output else []
            txts = [line[1] for line in result] if result else []
        if not txts:
            return ""
        return "\n".join(str(t) for t in txts)


# ---------------------------------------------------------------------- #
# V0.2.1 云端 MiniMax OCR 后端
# ---------------------------------------------------------------------- #
class CloudMinimaxOCR:
    """云端 MiniMax Vision OCR 后端。

    包装现有 `ocr_with_minimax` 函数以满足 OCRBackend 协议。
    空文本、超时、未配置均视为失败抛 RuntimeError，由 orchestrator 触发回退。
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


# ---------------------------------------------------------------------- #
# V0.2.1 OCR 调度器（云端优先 + 本地兜底）
# ---------------------------------------------------------------------- #
class OCROrchestrator:
    """OCR 后端调度器：按顺序尝试，失败回退。

    优先级：
        1. CloudMinimaxOCR（仅当 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID 都配置）
        2. LocalRapidOCR（兜底，无 key 或云端失败时启用）

    本地 OCR 受 semaphore 限制并发。
    """
    def __init__(self):
        import asyncio

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


# ---------------------------------------------------------------------- #
# 正则提取：价格、重量、数量、日期
# ---------------------------------------------------------------------- #
# 价格：匹配 "¥19.9" "19.9元" "到手价19.9" "券后价19.9" 等
_PRICE_PATTERNS = [
    re.compile(r'(?:到手价|券后价|实付|售价|价[：:]?)\s*[¥￥]?\s*(\d+\.?\d*)', re.I),
    re.compile(r'[¥￥]\s*(\d+\.?\d*)'),
    re.compile(r'(\d+\.?\d*)\s*元'),
]

# 重量：匹配 "500g" "420克" "净含量420g" "84g×5袋" "84g*5" "5kg"
_WEIGHT_PATTERNS = [
    re.compile(r'净含量\s*[：:]?\s*(\d+(?:\.\d+)?)\s*(g|克|kg|KG|毫升|ml)', re.I),
    re.compile(r'(\d+(?:\.\d+)?)\s*(g|克|kg|KG)\s*[×x\*]\s*(\d+)', re.I),  # 84g×5
    re.compile(r'(\d+(?:\.\d+)?)\s*(g|克|kg|KG|毫升|ml)', re.I),
]

# 数量：匹配 "5袋" "10包" "×5" "*5"
_QUANTITY_PATTERNS = [
    re.compile(r'[×x\*]\s*(\d+)\s*(?:袋|包|盒|罐|支|条|片|个|瓶|杯|份|装)', re.I),
    re.compile(r'(\d+)\s*(?:袋|包|盒|罐|支|条|片|个|瓶|杯|份|装)', re.I),
]

# 日期：匹配 "2026-09-01" "2026/09/01" "保质期至2026.09.01" 等
_DATE_PATTERNS = [
    re.compile(r'(?:保质期[至到]?|到期[日]?|到期[：:]?|生产日期[：:]?)\s*(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})', re.I),
    re.compile(r'(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})\s*[日号]?'),
]

# ---------------------------------------------------------------------- #
# 关键词规则：口味类型、包装类型
# ---------------------------------------------------------------------- #
_RANDOM_KEYWORDS = ["随机", "混发", "混合", "盲盒", "随机发", "随机口味", "口味随机", "混搭"]
_FIXED_KEYWORDS = ["指定口味", "固定口味", "自选口味"]

_PACKAGE_MAP = {
    "袋": "bag", "包": "bag", "盒": "box", "碗": "bowl", "罐": "box",
    "瓶": "box", "杯": "bowl", "桶": "box",
}


def _extract_price(text: str) -> FieldCandidate:
    """提取价格，优先取"到手价/券后价"，其次取第一个价格。"""
    best: Optional[float] = None
    source = ""
    for pat in _PRICE_PATTERNS:
        m = pat.search(text)
        if m:
            val = float(m.group(1))
            if best is None or val < best or "到手" in m.group(0) or "券后" in m.group(0):
                best = val
                source = m.group(0).strip()
    if best is not None:
        return FieldCandidate(value=f"{best:.2f}", confidence="high", source=source)
    return FieldCandidate(confidence="low")


def _extract_weight(text: str) -> FieldCandidate:
    """提取重量（克），处理 84g×5袋、5kg 等格式。"""
    for pat in _WEIGHT_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        groups = m.groups()
        # 84g×5 格式：3 个捕获组 (数值, 单位, 数量)
        if len(groups) == 3:
            unit_weight = float(groups[0])
            unit_str = groups[1].lower()
            qty = int(groups[2])
            if unit_str in ("kg",):
                unit_weight *= 1000
            total = unit_weight * qty
            return FieldCandidate(value=f"{total:.0f}", confidence="high", source=m.group(0).strip())
        # 2 个捕获组 (数值, 单位)
        elif len(groups) == 2:
            unit_str = groups[1].lower()
            val = float(groups[0])
            if unit_str in ("kg",):
                val *= 1000
            return FieldCandidate(value=f"{val:.0f}", confidence="high", source=m.group(0).strip())
        else:
            val = float(groups[0])
            if "kg" in m.group(0).lower() and "g" not in m.group(0).lower().replace("kg", ""):
                val *= 1000
            return FieldCandidate(value=f"{val:.0f}", confidence="high", source=m.group(0).strip())
    return FieldCandidate(confidence="low")


def _extract_quantity(text: str) -> FieldCandidate:
    """提取数量。"""
    for pat in _QUANTITY_PATTERNS:
        m = pat.search(text)
        if m:
            return FieldCandidate(value=m.group(1), confidence="medium", source=m.group(0).strip())
    return FieldCandidate(confidence="low")


def _extract_expiry(text: str) -> FieldCandidate:
    """提取到期日。"""
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                iso = date(y, mo, d).isoformat()
                conf = "high" if "到期" in m.group(0) or "保质期" in m.group(0) else "medium"
                return FieldCandidate(value=iso, confidence=conf, source=m.group(0).strip())
            except ValueError:
                continue
    return FieldCandidate(confidence="low")


def _extract_flavor_type(text: str) -> FieldCandidate:
    """判断口味类型：random / fixed / unknown。"""
    for kw in _RANDOM_KEYWORDS:
        if kw in text:
            return FieldCandidate(value="random", confidence="medium", source=kw)
    for kw in _FIXED_KEYWORDS:
        if kw in text:
            return FieldCandidate(value="fixed", confidence="medium", source=kw)
    return FieldCandidate(value="unknown", confidence="low")


def _extract_flavor_name(text: str) -> FieldCandidate:
    """尝试提取具体口味名称。"""
    patterns = [
        re.compile(r'口味[：:]?\s*([^\s,，、/]+(?:味|巧|莓|茶|辣|咸|甜|酸|苦|葱|蒜|椒|蜜|奶|椰|抹茶|可可|芝士|海苔|芥末|烧烤|番茄|香辣|麻辣|原味|黑巧|白巧|草莓|蓝莓|芒果|柠檬|葡萄|橙|苹果|香蕉|西瓜|哈密瓜|榴莲|荔枝|桂圆|杨梅|樱桃|水蜜桃|百香果|树莓|黑加仑|青柠|西柚|柚子|石榴|猕猴桃|火龙果|木瓜|椰子|菠萝|菠萝蜜|山竹|莲雾|番石榴|释迦|杨桃|枇杷|桑葚|青梅|李子|杏|枣|山楂|核桃|杏仁|腰果|榛子|开心果|巴旦木|花生|瓜子|松子|夏威夷果|碧根果|蔓越莓|枸杞|红枣|桂圆|莲子|百合|银耳|芝麻|燕麦|紫薯|红薯|玉米|南瓜|芋头|山药|红豆|绿豆|黑豆|芸豆|鹰嘴豆|豌豆|蚕豆|毛豆|扁豆|豇豆|四季豆|荷兰豆|刀豆|蛇豆|猫耳朵|牛耳仔|锅巴|麻花|蛋卷|饼干|曲奇|蛋糕|面包|吐司|法棍|贝果|松饼|华夫|司康|马芬|布朗尼|提拉米苏|慕斯|布丁|果冻|酸奶|冰淇淋|雪糕|棒冰|沙冰|奶昔|奶茶|果茶|花茶|绿茶|红茶|乌龙茶|白茶|黑茶|普洱|龙井|碧螺春|铁观音|大红袍|茉莉花|菊花|玫瑰|桂花|薰衣草|洋甘菊|洛神花|百香果|金桔|柠檬草|薄荷|迷迭香|百里香|罗勒|紫苏|牛至|莳萝|茴香|肉桂|丁香|豆蔻|八角|花椒|胡椒|辣椒|姜黄|咖喱|孜然|芝麻|罂粟籽))', re.I),
        re.compile(r'([^\s,，、/]+(?:味))\s*(?:口味|口味[：:]?)', re.I),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            name = m.group(1).strip()
            if len(name) <= 10:
                return FieldCandidate(value=name, confidence="low", source=m.group(0).strip())
    return FieldCandidate(confidence="low")


def _extract_package_type(text: str) -> FieldCandidate:
    """提取包装类型。"""
    for kw, pkg in _PACKAGE_MAP.items():
        if kw in text:
            return FieldCandidate(value=pkg, confidence="medium", source=kw)
    return FieldCandidate(value="unknown", confidence="low")


# ---------------------------------------------------------------------- #
# 主提取函数
# ---------------------------------------------------------------------- #
def extract_fields_from_text(text: str) -> ExtractedFields:
    """从 OCR 文本中提取结构化字段。"""
    return ExtractedFields(
        total_price=_extract_price(text),
        total_weight_g=_extract_weight(text),
        flavor_type=_extract_flavor_type(text),
        flavor_name=_extract_flavor_name(text),
        expiry_date=_extract_expiry(text),
        quantity=_extract_quantity(text),
        package_type=_extract_package_type(text),
        raw_text=text,
    )


# ---------------------------------------------------------------------- #
# MiniMax Vision OCR 后端
# ---------------------------------------------------------------------- #
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"


async def ocr_with_minimax(image_bytes: bytes, filename: str = "screenshot.jpg") -> str:
    """调用 MiniMax Vision API 提取图片中的文本。

    返回 OCR 原始文本，供后续正则/规则提取。
    """
    if not MINIMAX_API_KEY or not MINIMAX_GROUP_ID:
        raise RuntimeError("MINIMAX_API_KEY 或 MINIMAX_GROUP_ID 未配置，请在环境变量中设置")

    b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": "MiniMax-Vision-01",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "请仔细提取这张商品截图中的所有文字信息，"
                            "重点关注：价格（到手价/券后价/原价）、重量/净含量、"
                            "口味（是否随机/混发）、到期日/保质期、数量/包装规格。"
                            "请按原文输出，不要遗漏任何文字。"
                        ),
                    },
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{MINIMAX_BASE_URL}/text/chatcompletion_vision?GroupId={MINIMAX_GROUP_ID}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return ""


def ocr_with_minimax_sync(image_bytes: bytes) -> str:
    """同步版本的 MiniMax Vision OCR。"""
    if not MINIMAX_API_KEY or not MINIMAX_GROUP_ID:
        raise RuntimeError("MINIMAX_API_KEY 或 MINIMAX_GROUP_ID 未配置")

    b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": "MiniMax-Vision-01",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "请仔细提取这张商品截图中的所有文字信息，"
                            "重点关注：价格（到手价/券后价/原价）、重量/净含量、"
                            "口味（是否随机/混发）、到期日/保质期、数量/包装规格。"
                            "请按原文输出，不要遗漏任何文字。"
                        ),
                    },
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{MINIMAX_BASE_URL}/text/chatcompletion_vision?GroupId={MINIMAX_GROUP_ID}"

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return ""


# ---------------------------------------------------------------------- #
# 完整流水线：图片 → OCR → 提取 → 结构化候选
# ---------------------------------------------------------------------- #
async def extract_from_image(image_bytes: bytes) -> ExtractedFields:
    """从图片提取字段：OCR → 正则/规则提取。"""
    raw_text = await ocr_with_minimax(image_bytes)
    if not raw_text.strip():
        return ExtractedFields(raw_text="(OCR 未返回文本)")
    return extract_fields_from_text(raw_text)


def extract_from_image_sync(image_bytes: bytes) -> ExtractedFields:
    """同步版本：图片 → OCR → 提取。"""
    raw_text = ocr_with_minimax_sync(image_bytes)
    if not raw_text.strip():
        return ExtractedFields(raw_text="(OCR 未返回文本)")
    return extract_fields_from_text(raw_text)


# ---------------------------------------------------------------------- #
# 序列化
# ---------------------------------------------------------------------- #
def extracted_to_dict(ef: ExtractedFields) -> dict:
    """将 ExtractedFields 转为可 JSON 序列化的字典。"""
    def _fc(fc: FieldCandidate) -> dict:
        return {"value": fc.value, "confidence": fc.confidence, "source": fc.source}
    return {
        "total_price": _fc(ef.total_price),
        "total_weight_g": _fc(ef.total_weight_g),
        "flavor_type": _fc(ef.flavor_type),
        "flavor_name": _fc(ef.flavor_name),
        "expiry_date": _fc(ef.expiry_date),
        "quantity": _fc(ef.quantity),
        "package_type": _fc(ef.package_type),
        "raw_text": ef.raw_text,
    }
