"""数据模型定义：商品、用户偏好、评估结果。"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Literal, List


FlavorType = Literal["fixed", "random", "unknown"]
PackageType = Literal["bag", "bowl", "box", "unknown"]


@dataclass
class SnackItem:
    """单个临期零食商品。"""
    name: str
    total_price: float
    total_weight_g: float
    flavor_type: FlavorType
    flavor_name: Optional[str] = None
    expiry_date: Optional[date] = None
    package_type: PackageType = "unknown"
    quantity: Optional[int] = None
    source_text: Optional[str] = None


@dataclass
class UserPreference:
    """用户口味偏好与日均消耗量。"""
    preferred_flavors: List[str] = field(default_factory=list)
    disliked_flavors: List[str] = field(default_factory=list)
    daily_intake_g: float = 20.0


@dataclass
class EvaluationResult:
    """单个商品的完整评估结果。"""
    item: SnackItem
    price_per_g: float
    price_per_pack: Optional[float]
    flavor_factor: float
    expiry_factor: float
    adjusted_price_per_g: float
    value_score: float
    risk_level: str
    estimated_days_to_finish: Optional[float]
    days_until_expiry: Optional[int]
    recommendation_label: str
    reason: str
    baseline_updated: bool
