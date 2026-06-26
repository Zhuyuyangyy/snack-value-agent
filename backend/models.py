"""数据模型：SnackItem + UserPreference + EvaluationResult（Pydantic v2）。

V0.3：SnackItem 扩展到 24 字段，新增 4 类 flavor_type（fixed/random/mixed/unknown）。
为保持向后兼容，保留 `total_price`（deprecated），新增 `final_price`。
"""
from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------- #
# V0.3 枚举类型
# ---------------------------------------------------------------------- #
FlavorType = Literal["fixed", "random", "mixed", "unknown"]
PackageType = Literal["bag", "box", "bowl", "bottle", "can", "unknown"]
Channel = Literal["taobao", "tmall", "jd", "pdd", "douyin", "kuaishou", "offline", "unknown"]
Category = Literal[
    "chocolate", "cookie", "chips", "candy", "beverage",
    "jerky", "cake", "nuts", "instant_food", "other", "unknown"
]
AfterOpeningRisk = Literal["low", "medium", "high", "unknown"]
ExpiryRiskLevel = Literal["low", "medium", "high", "extreme", "unknown", "expired"]


class SnackItem(BaseModel):
    """零食商品（V0.3：24 字段 P0+P1 子集）。"""
    # 基础
    name: str
    # 价格（P0）
    final_price: Optional[float] = Field(default=None, gt=0, description="到手价")
    total_price: Optional[float] = Field(None, gt=0, description="标价（deprecated，兼容老请求）")
    listed_price: Optional[float] = Field(None, gt=0, description="标价（页面价）")
    coupon_amount: Optional[float] = Field(0, ge=0, description="优惠券")
    discount_amount: Optional[float] = Field(0, ge=0, description="满减")
    shipping_fee: Optional[float] = Field(0, ge=0, description="运费")
    # 规格
    total_weight_g: float = Field(..., gt=0)
    single_weight_g: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    package_type: PackageType = "unknown"
    # 口味
    flavor_type: FlavorType = "unknown"
    flavor_name: Optional[str] = None
    # 临期
    expiry_date: Optional[date] = None
    estimated_delivery_days: int = Field(3, ge=0, le=30)
    # 分类/品牌
    channel: Channel = "unknown"
    category: Category = "unknown"
    brand: Optional[str] = None
    after_opening_risk: AfterOpeningRisk = "unknown"
    # 元数据
    source_text: Optional[str] = None
    source_url: Optional[str] = None
    # V0.3 OCR 可信度（可选字典）
    field_confidences: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("name 不能为空")
        return s

    @model_validator(mode="before")
    @classmethod
    def backfill_final_price(cls, data):
        """向后兼容：若仅传 total_price（无 final_price），则把 total_price 同步给 final_price。

        - 优先使用显式 final_price。
        - 否则用 total_price。
        - 都不存在则抛错（必填之一）。
        """
        if isinstance(data, dict):
            fp = data.get("final_price")
            tp = data.get("total_price")
            if fp is None and tp is not None:
                data["final_price"] = tp
        return data

    @model_validator(mode="after")
    def final_price_required(self) -> "SnackItem":
        if self.final_price is None:
            raise ValueError("final_price 或 total_price 至少需要一个且 > 0")
        return self


class UserPreference(BaseModel):
    """用户偏好。"""
    preferred_flavors: List[str] = Field(default_factory=list)
    disliked_flavors: List[str] = Field(default_factory=list)
    daily_intake_g: float = 20.0


class EvaluationResult(BaseModel):
    """单次评估结果（向后兼容 + V0.3 新字段）。"""
    item: SnackItem
    price_per_g: float
    price_per_pack: Optional[float] = None
    flavor_factor: float
    expiry_factor: float
    adjusted_price_per_g: float
    value_score: float
    risk_level: str
    estimated_days_to_finish: Optional[float] = None
    days_until_expiry: Optional[int] = None
    recommendation_label: str
    reason: str
    baseline_updated: bool

    # V0.3 新增（可选，保持向后兼容）
    price_per_100g: Optional[float] = None
    required_daily_intake_g: Optional[float] = None
    usable_days_until_expiry: Optional[int] = None
    finish_ratio: Optional[float] = None
    expiry_risk_level: Optional[str] = None
    logistics_factor: Optional[float] = None
    trust_factor: Optional[float] = None
    missing_info_factor: Optional[float] = None
    real_value_price_per_g: Optional[float] = None
    price_score: Optional[float] = None
    expiry_score: Optional[float] = None
    preference_score: Optional[float] = None
    trust_score: Optional[float] = None
    final_score: Optional[float] = None
    missing_fields: Optional[List[str]] = None
    field_confidences: Optional[dict] = None
