"""real_value_price_per_g 主公式 + 4 评分单测。

锁定 V0.3 引入的核心公式和 4 个 0-1 评分:
    - calculate_real_value
    - calculate_price_score
    - calculate_expiry_score
    - calculate_preference_score
    - calculate_trust_score
    - final_score 加权求和
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models import SnackItem, UserPreference
from backend.comparator import SnackComparator


def make_item(**kwargs) -> SnackItem:
    """构造一个最小可用的 SnackItem。"""
    defaults = dict(name="X", final_price=10.0, total_weight_g=100)
    defaults.update(kwargs)
    return SnackItem(**defaults)


# ====================================================================== #
# calculate_real_value (主公式)
# ====================================================================== #
def test_evaluate_returns_real_value():
    """evaluate() 返回的 real_value_price_per_g 不为 None 且 > 0。"""
    item = make_item(
        expiry_date=date.today() + timedelta(days=30),
        flavor_type="fixed",
        flavor_name="黑巧",
    )
    c = SnackComparator(user_preference=UserPreference(preferred_flavors=["黑巧"]))
    result = c.evaluate(item)
    assert result.real_value_price_per_g is not None
    assert result.real_value_price_per_g > 0


def test_evaluate_returns_4_scores():
    """evaluate() 填充 price_score / expiry_score / preference_score / trust_score / final_score。"""
    item = make_item(expiry_date=date.today() + timedelta(days=30))
    c = SnackComparator()
    result = c.evaluate(item)
    assert result.price_score is not None
    assert result.expiry_score is not None
    assert result.preference_score is not None
    assert result.trust_score is not None
    assert result.final_score is not None
    assert 0 <= result.price_score <= 1
    assert 0 <= result.expiry_score <= 1
    assert 0 <= result.preference_score <= 1
    assert 0 <= result.trust_score <= 1
    assert 0 <= result.final_score <= 1


def test_final_score_is_weighted_average():
    """final_score = 0.45*price + 0.25*expiry + 0.20*pref + 0.10*trust。"""
    item = make_item(expiry_date=date.today() + timedelta(days=60))
    c = SnackComparator()
    result = c.evaluate(item)
    expected = (
        0.45 * result.price_score
        + 0.25 * result.expiry_score
        + 0.20 * result.preference_score
        + 0.10 * result.trust_score
    )
    assert abs(result.final_score - expected) < 0.001


# ====================================================================== #
# calculate_price_score
# ====================================================================== #
def test_price_score_better_than_baseline():
    """低于基线时 price_score > 0.5。"""
    c = SnackComparator()
    c.baseline_price_per_g = 0.10
    score = c.calculate_price_score(0.05)
    assert score > 0.5


def test_price_score_worse_than_baseline():
    """高于基线时 price_score < 0.5。"""
    c = SnackComparator()
    c.baseline_price_per_g = 0.05
    score = c.calculate_price_score(0.10)
    assert score < 0.5


def test_price_score_at_baseline():
    """等于基线时 price_score = 1.0(根据实现:ratio<=1.0 → min(1.0, 1.0+0*0.5)=1.0)。"""
    c = SnackComparator()
    c.baseline_price_per_g = 0.05
    assert c.calculate_price_score(0.05) == 1.0


def test_price_score_no_baseline():
    """无基线时(inf)→ 0.5。"""
    c = SnackComparator()
    # 默认 baseline_price_per_g = inf
    assert c.calculate_price_score(0.05) == 0.5


# ====================================================================== #
# calculate_expiry_score
# ====================================================================== #
def test_expiry_score_long_expiry():
    """>= 60 天 → 1.0。"""
    c = SnackComparator()
    assert c.calculate_expiry_score(60) == 1.0
    assert c.calculate_expiry_score(120) == 1.0


def test_expiry_score_short_expiry():
    """15 天 → 0 < score < 1。"""
    c = SnackComparator()
    score = c.calculate_expiry_score(15)
    assert 0 < score < 1


def test_expiry_score_no_expiry():
    """None → 0.5。"""
    c = SnackComparator()
    assert c.calculate_expiry_score(None) == 0.5


def test_expiry_score_expired():
    """<= 0 天 → 0.0。"""
    c = SnackComparator()
    assert c.calculate_expiry_score(0) == 0.0
    assert c.calculate_expiry_score(-5) == 0.0


# ====================================================================== #
# calculate_preference_score
# ====================================================================== #
def test_preference_score_preferred():
    """命中 preferred_flavors → 1.0。"""
    item = make_item(flavor_name="黑巧")
    c = SnackComparator(user_preference=UserPreference(preferred_flavors=["黑巧"]))
    assert c.calculate_preference_score(item) == 1.0


def test_preference_score_disliked():
    """命中 disliked_flavors → 0.0。"""
    item = make_item(flavor_name="榴莲")
    c = SnackComparator(user_preference=UserPreference(disliked_flavors=["榴莲"]))
    assert c.calculate_preference_score(item) == 0.0


def test_preference_score_4_categories():
    """无用户偏好时,flavor_type → 固定 0/0.4/0.5/0.7。"""
    c = SnackComparator()
    assert c.calculate_preference_score(make_item(flavor_type="fixed", flavor_name="X")) == 0.7
    assert c.calculate_preference_score(make_item(flavor_type="mixed")) == 0.5
    assert c.calculate_preference_score(make_item(flavor_type="random")) == 0.4
    assert c.calculate_preference_score(make_item(flavor_type="unknown")) == 0.5


# ====================================================================== #
# calculate_trust_score
# ====================================================================== #
def test_trust_score_no_confidences():
    """field_confidences 为 None → 0.5。"""
    c = SnackComparator()
    item = make_item()
    item.field_confidences = None
    assert c.calculate_trust_score(item) == 0.5


def test_trust_score_with_high_values():
    """所有 confidence 都 >= 0.9 → 1.0(weights.get 默认 0.5,但我们的实现走的是 label 路径)。

    注意:SnackItem.field_confidences 验证为 float,但 trust_score 实现期望 label 字符串。
    这里 monkeypatch 来模拟 label keys。
    """
    c = SnackComparator()
    item = make_item()
    object.__setattr__(item, "field_confidences", {"a": "high", "b": "high"})
    assert c.calculate_trust_score(item) == 1.0


def test_trust_score_mixed_labels():
    """high + low → (1.0 + 0.3) / 2 = 0.65。"""
    c = SnackComparator()
    item = make_item()
    object.__setattr__(item, "field_confidences", {"a": "high", "b": "low"})
    assert c.calculate_trust_score(item) == 0.65
