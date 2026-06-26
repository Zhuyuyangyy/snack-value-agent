"""5 个因子函数单测。

锁定 V0.3 引入的 5 因子方法行为:
    - flavor_factor_v23
    - expiry_factor_v23
    - logistics_factor
    - trust_factor
    - missing_info_factor
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
# flavor_factor_v23
# ====================================================================== #
def test_flavor_factor_preferred_flavor():
    """命中 preferred_flavors → 0.95。"""
    item = make_item(flavor_type="fixed", flavor_name="黑巧")
    pref = UserPreference(preferred_flavors=["黑巧"])
    c = SnackComparator(user_preference=pref)
    assert c.flavor_factor_v23(item) == 0.95


def test_flavor_factor_disliked_flavor():
    """命中 disliked_flavors → 1.12。"""
    item = make_item(flavor_type="fixed", flavor_name="榴莲")
    pref = UserPreference(disliked_flavors=["榴莲"])
    c = SnackComparator(user_preference=pref)
    assert c.flavor_factor_v23(item) == 1.12


def test_flavor_factor_4_categories():
    """无用户偏好时,4 种 flavor_type 各有独立系数。"""
    c = SnackComparator()
    assert c.flavor_factor_v23(make_item(flavor_type="fixed")) == 1.00
    assert c.flavor_factor_v23(make_item(flavor_type="mixed")) == 1.04
    assert c.flavor_factor_v23(make_item(flavor_type="random")) == 1.08
    assert c.flavor_factor_v23(make_item(flavor_type="unknown")) == 1.10


# ====================================================================== #
# expiry_factor_v23
# ====================================================================== #
def test_expiry_factor_no_expiry():
    """无 expiry_date → 1.12 (未知风险)。"""
    c = SnackComparator()
    assert c.expiry_factor_v23(make_item()) == 1.12


def test_expiry_factor_low_risk():
    """150 天后到期,daily_intake=20g,100g → finish_ratio=100/147≈0.68 (中风险)。

    注意:要看 < 0.5 才算低风险,这里应得 1.08 而非 1.00。
    改用 daily_intake=100 制造真正的低风险场景。
    """
    future = date.today() + timedelta(days=150)
    pref = UserPreference(daily_intake_g=100.0)  # 100g/天
    c = SnackComparator(user_preference=pref)
    # estimated = 100/100 = 1 天,usable = 150-3 = 147,finish_ratio ≈ 0.0068 → 低风险
    assert c.expiry_factor_v23(make_item(expiry_date=future)) == 1.00


def test_expiry_factor_high_risk():
    """10 天后到期,500g 总重 → finish_ratio 高 → >= 1.20。"""
    future = date.today() + timedelta(days=10)
    c = SnackComparator()
    # estimated = 500/20 = 25,usable = 10-3 = 7,finish_ratio ≈ 3.57 → 1.50
    f = c.expiry_factor_v23(make_item(expiry_date=future, total_weight_g=500))
    assert f >= 1.20


def test_expiry_factor_expired():
    """已过期(usable <= 0)→ 999.0。"""
    past = date.today() - timedelta(days=1)
    c = SnackComparator()
    assert c.expiry_factor_v23(make_item(expiry_date=past)) == 999.0


# ====================================================================== #
# logistics_factor
# ====================================================================== #
def test_logistics_factor_no_shipping():
    """shipping_fee=0 → 1.0。"""
    c = SnackComparator()
    assert c.logistics_factor(make_item(shipping_fee=0)) == 1.0


def test_logistics_factor_high_shipping_ratio():
    """运费 > 20% 价格 → 1.10。"""
    c = SnackComparator()
    f = c.logistics_factor(make_item(final_price=10, shipping_fee=3))
    assert f >= 1.10


def test_logistics_factor_chocolate_high_risk():
    """chocolate + after_opening_risk=high → 1.05。"""
    c = SnackComparator()
    f = c.logistics_factor(make_item(category="chocolate", after_opening_risk="high"))
    assert f > 1.0


# ====================================================================== #
# trust_factor
# ====================================================================== #
def test_trust_factor_no_confidences():
    """field_confidences 为 None → 1.10 (保守惩罚)。"""
    c = SnackComparator()
    item = make_item()
    item.field_confidences = None
    assert c.trust_factor(item) == 1.10


def test_trust_factor_empty_confidences():
    """field_confidences 为空字典 → 1.10。"""
    c = SnackComparator()
    item = make_item()
    item.field_confidences = {}
    assert c.trust_factor(item) == 1.10


def test_trust_factor_with_label_keys():
    """trust_factor 期望字符串标签键 {high, medium, low}。

    注意:当前 SnackItem.field_confidences 验证为 float,
    所以这里我们 monkeypatch 它以模拟标签键场景,验证 score_map 行为。
    """
    c = SnackComparator()
    item = make_item()
    # 模拟 label keys(实际生产中要扩展 validator,这里直接 setattr)
    object.__setattr__(item, "field_confidences", {"price": "high", "weight": "high"})
    assert c.trust_factor(item) == 1.0


def test_trust_factor_returns_float():
    """trust_factor 总是返回 float 类型。"""
    c = SnackComparator()
    item = make_item()
    item.field_confidences = None
    val = c.trust_factor(item)
    assert isinstance(val, float)
    assert val >= 1.0


# ====================================================================== #
# missing_info_factor
# ====================================================================== #
def test_missing_info_all_present():
    """所有关键字段都有(expiry_date, flavor_name, brand)→ 1.0。"""
    c = SnackComparator()
    item = make_item(
        flavor_type="fixed",
        flavor_name="X",
        brand="Y",
        expiry_date=date.today() + timedelta(days=30),
    )
    assert c.missing_info_factor(item) == 1.0


def test_missing_info_no_expiry():
    """无 expiry_date → >= 1.20。"""
    c = SnackComparator()
    item = make_item()
    assert c.missing_info_factor(item) >= 1.20


def test_missing_info_no_brand():
    """无 brand(其他字段齐)→ >= 1.05。"""
    c = SnackComparator()
    item = make_item(expiry_date=date.today(), flavor_name="X")
    assert c.missing_info_factor(item) >= 1.05
