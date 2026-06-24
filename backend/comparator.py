"""核心比价算法：克单价 → 口味系数 → 临期风险系数 → 调整后克单价 → 有效价值评分 → 推荐排序。"""
from datetime import date
from typing import Optional, List

from .models import SnackItem, UserPreference, EvaluationResult


class SnackComparator:
    """临期零食综合价值评估器。

    核心公式：
        adjusted_price_per_g = price_per_g * flavor_factor * expiry_factor
        value_score = baseline_price_per_g / adjusted_price_per_g
    """

    def __init__(self, user_preference: Optional[UserPreference] = None):
        self.baseline_price_per_g: float = float("inf")
        self.baseline_source: Optional[str] = None
        self.user_preference = user_preference or UserPreference()

    # ------------------------------------------------------------------ #
    # 基础计算
    # ------------------------------------------------------------------ #
    def calculate_price_per_g(self, item: SnackItem) -> float:
        if item.total_weight_g <= 0:
            raise ValueError("total_weight_g 必须大于 0")
        return item.total_price / item.total_weight_g

    def calculate_price_per_pack(self, item: SnackItem) -> Optional[float]:
        if item.quantity and item.quantity > 0:
            return item.total_price / item.quantity
        return None

    # ------------------------------------------------------------------ #
    # 口味系数
    # ------------------------------------------------------------------ #
    def get_flavor_factor(self, item: SnackItem) -> float:
        """随机/未知口味必须比固定口味更便宜才值得买。"""
        if item.flavor_type == "random":
            return 1.05
        if item.flavor_type == "unknown":
            return 1.06

        flavor = (item.flavor_name or "").strip()
        if flavor in self.user_preference.preferred_flavors:
            return 0.95
        if flavor in self.user_preference.disliked_flavors:
            return 1.08
        return 1.00

    # ------------------------------------------------------------------ #
    # 临期风险系数
    # ------------------------------------------------------------------ #
    def get_expiry_factor_and_risk(
        self, item: SnackItem, today: Optional[date] = None
    ) -> tuple[float, str, Optional[float], Optional[int]]:
        """返回 (系数, 风险等级, 预计吃完天数, 距到期天数)。"""
        today = today or date.today()

        if item.expiry_date is None:
            return 1.12, "未知风险", None, None

        days_until_expiry = (item.expiry_date - today).days

        if days_until_expiry <= 0:
            return 999.0, "已过期", None, days_until_expiry

        estimated_days_to_finish = item.total_weight_g / self.user_preference.daily_intake_g
        finish_ratio = estimated_days_to_finish / days_until_expiry

        if finish_ratio < 0.5:
            return 1.00, "低风险", estimated_days_to_finish, days_until_expiry
        if finish_ratio <= 0.8:
            return 1.08, "中风险", estimated_days_to_finish, days_until_expiry
        return 1.20, "高风险", estimated_days_to_finish, days_until_expiry

    # ------------------------------------------------------------------ #
    # 推荐标签生成
    # ------------------------------------------------------------------ #
    def generate_recommendation(
        self,
        item: SnackItem,
        price_per_g: float,
        adjusted_price_per_g: float,
        risk_level: str,
        baseline_updated: bool,
        prev_baseline: float,
    ) -> tuple[str, str]:
        if risk_level == "已过期":
            return "❌ 不推荐", "商品已过期，不建议购买。"

        if baseline_updated:
            if prev_baseline != float("inf") and prev_baseline > 0:
                saving_pct = (prev_baseline - price_per_g) / prev_baseline * 100
                return "🔥 刷新历史低价", f"该商品原始克单价低于历史基线，比之前低 {saving_pct:.2f}%，价格非常有竞争力。"
            return "🔥 刷新历史低价", "该商品原始克单价低于历史基线，价格非常有竞争力。"

        if self.baseline_price_per_g == float("inf"):
            return "✅ 可参考", "暂无历史基线，已将该商品作为初始参考。"

        price_ratio = price_per_g / self.baseline_price_per_g

        if price_ratio <= 1.05 and risk_level == "低风险":
            return "🥇 强推荐", "价格接近历史低价，且临期风险较低。"
        if price_ratio <= 1.05:
            return "✅ 可买", "价格接近历史低价，但需留意临期风险。"
        if price_ratio <= 1.15:
            return "⚠️ 可买但需看偏好", "价格略高，需要结合口味和保质期判断。"
        return "❌ 不推荐", "价格明显高于历史低价，除非特别喜欢该口味，否则不建议购买。"

    # ------------------------------------------------------------------ #
    # 单品评估
    # ------------------------------------------------------------------ #
    def evaluate(self, item: SnackItem, today: Optional[date] = None) -> EvaluationResult:
        price_per_g = self.calculate_price_per_g(item)
        price_per_pack = self.calculate_price_per_pack(item)

        flavor_factor = self.get_flavor_factor(item)
        expiry_factor, risk_level, est_days, days_left = self.get_expiry_factor_and_risk(item, today)

        adjusted_price_per_g = price_per_g * flavor_factor * expiry_factor

        if self.baseline_price_per_g == float("inf"):
            value_score = 1.0
        else:
            value_score = self.baseline_price_per_g / adjusted_price_per_g

        baseline_updated = False
        prev_baseline = self.baseline_price_per_g
        if risk_level != "已过期" and price_per_g < self.baseline_price_per_g:
            self.baseline_price_per_g = price_per_g
            self.baseline_source = item.name
            baseline_updated = True

        recommendation_label, reason = self.generate_recommendation(
            item=item,
            price_per_g=price_per_g,
            adjusted_price_per_g=adjusted_price_per_g,
            risk_level=risk_level,
            baseline_updated=baseline_updated,
            prev_baseline=prev_baseline,
        )

        return EvaluationResult(
            item=item,
            price_per_g=price_per_g,
            price_per_pack=price_per_pack,
            flavor_factor=flavor_factor,
            expiry_factor=expiry_factor,
            adjusted_price_per_g=adjusted_price_per_g,
            value_score=value_score,
            risk_level=risk_level,
            estimated_days_to_finish=est_days,
            days_until_expiry=days_left,
            recommendation_label=recommendation_label,
            reason=reason,
            baseline_updated=baseline_updated,
        )

    # ------------------------------------------------------------------ #
    # 批量评估并排序
    # ------------------------------------------------------------------ #
    def evaluate_many(self, items: List[SnackItem], today: Optional[date] = None) -> List[EvaluationResult]:
        results = [self.evaluate(item, today=today) for item in items]
        # 已过期的排到最后，其余按调整后克单价升序（越低越值）
        return sorted(
            results,
            key=lambda r: (r.risk_level == "已过期", r.adjusted_price_per_g),
        )
