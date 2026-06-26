"""核心比价算法：克单价 → 口味系数 → 临期风险系数 → 调整后克单价 → 有效价值评分 → 推荐排序。

V0.3：扩展为 5 因子 × 4 评分体系：
    real_value_price_per_g = price_per_g × flavor × expiry × logistics × trust × missing
    final_score = 0.45·price_score + 0.25·expiry_score + 0.20·preference_score + 0.10·trust_score
"""
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
    def _resolve_price(self, item: SnackItem) -> float:
        """V0.3：final_price 优先；老 total_price 兼容。"""
        if item.final_price is not None:
            return item.final_price
        if item.total_price is not None:
            return item.total_price
        raise ValueError("final_price 或 total_price 至少需要一个")

    def calculate_price_per_g(self, item: SnackItem) -> float:
        if item.total_weight_g <= 0:
            raise ValueError("total_weight_g 必须大于 0")
        return self._resolve_price(item) / item.total_weight_g

    def calculate_price_per_pack(self, item: SnackItem) -> Optional[float]:
        if item.quantity and item.quantity > 0:
            return self._resolve_price(item) / item.quantity
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
    # V0.3 评分权重
    # ------------------------------------------------------------------ #
    W_PRICE = 0.45
    W_EXPIRY = 0.25
    W_PREFERENCE = 0.20
    W_TRUST = 0.10

    # ------------------------------------------------------------------ #
    # V0.3 5 因子方法
    # ------------------------------------------------------------------ #
    def flavor_factor_v23(self, item: SnackItem) -> float:
        """flavor 因子（V0.3：4 类 + 用户偏好）。"""
        flavor = (item.flavor_name or "").strip()
        if flavor in self.user_preference.preferred_flavors:
            return 0.95
        if flavor in self.user_preference.disliked_flavors:
            return 1.12
        table = {"fixed": 1.00, "mixed": 1.04, "random": 1.08, "unknown": 1.10}
        return table.get(item.flavor_type, 1.10)

    def expiry_factor_v23(self, item: SnackItem) -> float:
        """expiry 因子（沿用 finish_ratio 逻辑，但 usable_days 扣物流时间）。"""
        usable = self._usable_days_v23(item)
        if usable is None:
            return 1.12  # 未知风险
        if usable <= 0:
            return 999.0
        estimated = item.total_weight_g / self.user_preference.daily_intake_g
        finish_ratio = estimated / usable
        if finish_ratio < 0.5:
            return 1.00
        if finish_ratio <= 0.8:
            return 1.08
        if finish_ratio <= 1.0:
            return 1.20
        return 1.50

    def logistics_factor(self, item: SnackItem) -> float:
        """logistics 因子（V0.3 新增）。"""
        base = 1.0
        if item.shipping_fee and item.shipping_fee > 0 and item.final_price > 0:
            ratio = item.shipping_fee / item.final_price
            if ratio > 0.20:
                base *= 1.10
            elif ratio > 0.10:
                base *= 1.05
        if item.category in ("chocolate", "cake") and item.after_opening_risk == "high":
            base *= 1.05
        return base

    def trust_factor(self, item: SnackItem) -> float:
        """trust 因子（V0.3 新增）。"""
        if not item.field_confidences:
            return 1.10
        score_map = {"high": 1.0, "medium": 1.05, "low": 1.20}
        confs = list(item.field_confidences.values())
        if not confs:
            return 1.10
        return sum(score_map.get(c, 1.10) for c in confs) / len(confs)

    def missing_info_factor(self, item: SnackItem) -> float:
        """missing_info 因子。"""
        factor = 1.0
        if item.expiry_date is None:
            factor *= 1.20
        if not item.flavor_name and item.flavor_type == "unknown":
            factor *= 1.10
        if item.brand is None:
            factor *= 1.05
        return factor

    def _usable_days_v23(self, item: SnackItem) -> Optional[int]:
        """到期可食用天数（扣除预计物流时间）。"""
        if item.expiry_date is None:
            return None
        days_until = (item.expiry_date - date.today()).days
        return max(0, days_until - item.estimated_delivery_days)

    # ------------------------------------------------------------------ #
    # V0.3 real_value 主公式
    # ------------------------------------------------------------------ #
    def calculate_real_value(self, item: SnackItem) -> float:
        """real_value_price_per_g 主公式。

        real_value = price_per_g × flavor × expiry × logistics × trust × missing
        """
        if item.total_weight_g <= 0 or item.final_price <= 0:
            return float("inf")
        price_per_g = item.final_price / item.total_weight_g
        return (
            price_per_g
            * self.flavor_factor_v23(item)
            * self.expiry_factor_v23(item)
            * self.logistics_factor(item)
            * self.trust_factor(item)
            * self.missing_info_factor(item)
        )

    # ------------------------------------------------------------------ #
    # V0.3 4 评分方法
    # ------------------------------------------------------------------ #
    def calculate_price_score(self, price_per_g: float) -> float:
        """克单价在历史区间的分位（0-1）。"""
        if self.baseline_price_per_g == float("inf"):
            return 0.5
        ratio = price_per_g / self.baseline_price_per_g
        if ratio <= 1.0:
            return min(1.0, 1.0 + (1.0 - ratio) * 0.5)
        return max(0.0, 1.0 - (ratio - 1.0) * 2.5)

    def calculate_expiry_score(self, usable_days: Optional[int]) -> float:
        """临期风险倒数（0-1）。"""
        if usable_days is None:
            return 0.5
        if usable_days <= 0:
            return 0.0
        return min(1.0, usable_days / 60.0)

    def calculate_preference_score(self, item: SnackItem) -> float:
        """口味匹配度（0-1）。"""
        flavor = (item.flavor_name or "").strip()
        if flavor in self.user_preference.preferred_flavors:
            return 1.0
        if flavor in self.user_preference.disliked_flavors:
            return 0.0
        return {"fixed": 0.7, "mixed": 0.5, "random": 0.4, "unknown": 0.5}.get(item.flavor_type, 0.5)

    def calculate_trust_score(self, item: SnackItem) -> float:
        """识别可信度（0-1）。"""
        if not item.field_confidences:
            return 0.5
        weights = {"high": 1.0, "medium": 0.6, "low": 0.3}
        scores = [weights.get(c, 0.5) for c in item.field_confidences.values()]
        return sum(scores) / len(scores) if scores else 0.5

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

        # V0.3: 计算多维度数据
        price_per_100g = price_per_g * 100
        usable = self._usable_days_v23(item)
        finish_ratio = None
        required_daily = None
        if usable is not None and usable > 0:
            estimated = item.total_weight_g / self.user_preference.daily_intake_g
            finish_ratio = estimated / usable
            required_daily = item.total_weight_g / usable

        flavor_f = self.flavor_factor_v23(item)
        expiry_f = self.expiry_factor_v23(item)
        logistics_f = self.logistics_factor(item)
        trust_f = self.trust_factor(item)
        missing_f = self.missing_info_factor(item)
        real_value = self.calculate_real_value(item)

        ps = self.calculate_price_score(price_per_g)
        es = self.calculate_expiry_score(usable)
        prs = self.calculate_preference_score(item)
        ts = self.calculate_trust_score(item)
        final_s = (
            ps * self.W_PRICE
            + es * self.W_EXPIRY
            + prs * self.W_PREFERENCE
            + ts * self.W_TRUST
        )

        missing_fields = []
        if item.expiry_date is None:
            missing_fields.append("expiry_date")
        if not item.flavor_name:
            missing_fields.append("flavor_name")
        if item.brand is None:
            missing_fields.append("brand")
        if item.quantity is None:
            missing_fields.append("quantity")

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
            # V0.3 新字段
            price_per_100g=price_per_100g,
            required_daily_intake_g=required_daily,
            usable_days_until_expiry=usable,
            finish_ratio=finish_ratio,
            logistics_factor=logistics_f,
            trust_factor=trust_f,
            missing_info_factor=missing_f,
            real_value_price_per_g=real_value,
            price_score=ps,
            expiry_score=es,
            preference_score=prs,
            trust_score=ts,
            final_score=final_s,
            missing_fields=missing_fields,
            field_confidences=item.field_confidences,
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
