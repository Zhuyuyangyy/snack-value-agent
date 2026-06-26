"""FastAPI 后端：手动输入 / 截图OCR → 字段确认 → 比价推荐 → 历史基线更新。"""
from datetime import date
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .comparator import SnackComparator
from .models import SnackItem, UserPreference
from .extractor import extract_fields_from_text, extract_from_image, extracted_to_dict
from .config import MAX_IMAGE_SIZE_BYTES
from . import database as db


app = FastAPI(title="SnackValue Agent", version="0.2.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------------- #
# 请求 / 响应模型
# ---------------------------------------------------------------------- #
class SnackItemIn(BaseModel):
    name: str
    total_price: float = Field(..., gt=0)
    total_weight_g: float = Field(..., gt=0)
    flavor_type: str = "fixed"  # fixed | random | unknown
    flavor_name: Optional[str] = None
    expiry_date: Optional[str] = None  # YYYY-MM-DD
    package_type: str = "unknown"
    quantity: Optional[int] = None
    source_text: Optional[str] = None


class CompareRequest(BaseModel):
    items: List[SnackItemIn]
    save: bool = True


class UserPreferenceIn(BaseModel):
    preferred_flavors: List[str] = []
    disliked_flavors: List[str] = []
    daily_intake_g: float = 20.0


class BaselineOut(BaseModel):
    baseline_price_per_g: Optional[float]
    baseline_source: Optional[str]


class ExtractTextIn(BaseModel):
    """手动粘贴 OCR 文本，走正则/规则提取。"""
    text: str


# ---------------------------------------------------------------------- #
# 启动初始化
# ---------------------------------------------------------------------- #
@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def _to_snack_item(item_in: SnackItemIn) -> SnackItem:
    expiry = None
    if item_in.expiry_date:
        try:
            expiry = date.fromisoformat(item_in.expiry_date)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"expiry_date 格式错误: {item_in.expiry_date}")
    return SnackItem(
        name=item_in.name,
        total_price=item_in.total_price,
        total_weight_g=item_in.total_weight_g,
        flavor_type=item_in.flavor_type,
        flavor_name=item_in.flavor_name,
        expiry_date=expiry,
        package_type=item_in.package_type,
        quantity=item_in.quantity,
        source_text=item_in.source_text,
    )


def _result_to_dict(result) -> dict:
    return {
        "name": result.item.name,
        "total_price": result.item.total_price,
        "total_weight_g": result.item.total_weight_g,
        "flavor_type": result.item.flavor_type,
        "flavor_name": result.item.flavor_name,
        "expiry_date": result.item.expiry_date.isoformat() if result.item.expiry_date else None,
        "quantity": result.item.quantity,
        "price_per_g": round(result.price_per_g, 6),
        "price_per_pack": round(result.price_per_pack, 4) if result.price_per_pack is not None else None,
        "flavor_factor": result.flavor_factor,
        "expiry_factor": result.expiry_factor,
        "adjusted_price_per_g": round(result.adjusted_price_per_g, 6),
        "value_score": round(result.value_score, 4),
        "risk_level": result.risk_level,
        "estimated_days_to_finish": round(result.estimated_days_to_finish, 1) if result.estimated_days_to_finish else None,
        "days_until_expiry": result.days_until_expiry,
        "recommendation_label": result.recommendation_label,
        "reason": result.reason,
        "baseline_updated": result.baseline_updated,
    }


# ---------------------------------------------------------------------- #
# API 路由
# ---------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/baseline")
def get_baseline():
    price, source = db.load_baseline()
    return BaselineOut(
        baseline_price_per_g=None if price == float("inf") else round(price, 6),
        baseline_source=source,
    )


@app.get("/api/history")
def get_history(limit: int = 50):
    return db.load_history(limit=limit)


@app.get("/api/preference")
def get_preference():
    return db.load_user_preference()


@app.put("/api/preference")
def put_preference(pref: UserPreferenceIn):
    db.save_user_preference(pref.preferred_flavors, pref.disliked_flavors, pref.daily_intake_g)
    return {"status": "ok", "preference": db.load_user_preference()}


@app.post("/api/compare")
def compare(req: CompareRequest):
    """批量比价：输入多个商品，输出排序后的推荐表，并更新历史基线。"""
    if not req.items:
        raise HTTPException(status_code=422, detail="items 不能为空")

    # 加载用户偏好与历史基线
    pref_dict = db.load_user_preference()
    user_pref = UserPreference(
        preferred_flavors=pref_dict["preferred_flavors"],
        disliked_flavors=pref_dict["disliked_flavors"],
        daily_intake_g=pref_dict["daily_intake_g"],
    )

    baseline_price, baseline_source = db.load_baseline()
    comparator = SnackComparator(user_preference=user_pref)
    comparator.baseline_price_per_g = baseline_price
    comparator.baseline_source = baseline_source

    items = [_to_snack_item(i) for i in req.items]
    results = comparator.evaluate_many(items)

    # 持久化 + 基线更新
    if req.save:
        for r in results:
            db.save_evaluation(r)
        if comparator.baseline_price_per_g != float("inf"):
            db.update_baseline(comparator.baseline_price_per_g, comparator.baseline_source or "")

    return {
        "baseline": {
            "price_per_g": None if comparator.baseline_price_per_g == float("inf") else round(comparator.baseline_price_per_g, 6),
            "source": comparator.baseline_source,
        },
        "results": [_result_to_dict(r) for r in results],
    }


# ------------------------------------------------------------------ #
# V0.2 截图 OCR 提取
# ------------------------------------------------------------------ #
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


@app.post("/api/extract_text")
def extract_from_pasted_text(body: ExtractTextIn):
    """手动粘贴 OCR 文本 → 正则/规则提取 → 返回候选字段 + 置信度。

    不依赖 MiniMax API，纯本地提取。
    """
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text 不能为空")
    fields = extract_fields_from_text(body.text)
    return extracted_to_dict(fields)


# ---------------------------------------------------------------------- #
# 前端静态资源
# ---------------------------------------------------------------------- #
@app.get("/")
def index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html 不存在")
    return FileResponse(index_path)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
