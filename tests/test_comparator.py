"""验收测试：覆盖 MVP 三个验收标准 + 核心算法边界。"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models import SnackItem, UserPreference
from backend.comparator import SnackComparator


TODAY = date(2026, 6, 24)


# ========================================================================== #
# 验收标准 1：能算清楚
# 输入 价格19.9 / 重量500g / 随机口味 / 到期2026-09-01
# 期望 克单价 0.0398，口味系数 1.05，低风险，调整后克单价 ≈ 0.0418
# ========================================================================== #
def test_acceptance_1_calculate_clearly():
    item = SnackItem(
        name="测试零食",
        total_price=19.9,
        total_weight_g=500,
        flavor_type="random",
        expiry_date=date(2026, 9, 1),
    )
    cmp = SnackComparator()
    r = cmp.evaluate(item, today=TODAY)

    assert abs(r.price_per_g - 0.0398) < 1e-6, f"克单价应为 0.0398，实际 {r.price_per_g}"
    assert abs(r.flavor_factor - 1.05) < 1e-6, "随机口味系数应为 1.05"
    assert r.risk_level == "低风险", f"临期风险应为低风险，实际 {r.risk_level}"
    expected_adjusted = 0.0398 * 1.05 * 1.00
    assert abs(r.adjusted_price_per_g - expected_adjusted) < 1e-6, "调整后克单价计算错误"


# ========================================================================== #
# 验收标准 2：能横向排序
# 输入 3 个商品，输出最优 / 备选 / 不推荐，并说明原因
# ========================================================================== #
def test_acceptance_2_horizontal_sort():
    items = [
        # 最便宜且低风险 → 应排第一
        SnackItem(name="A 便宜低风险", total_price=15.0, total_weight_g=500,
                  flavor_type="fixed", flavor_name="原味",
                  expiry_date=TODAY + timedelta(days=90)),
        # 中等价格 → 备选
        SnackItem(name="B 中等价", total_price=22.0, total_weight_g=500,
                  flavor_type="fixed", flavor_name="原味",
                  expiry_date=TODAY + timedelta(days=90)),
        # 最贵 → 不推荐
        SnackItem(name="C 最贵", total_price=35.0, total_weight_g=500,
                  flavor_type="fixed", flavor_name="原味",
                  expiry_date=TODAY + timedelta(days=90)),
    ]
    cmp = SnackComparator()
    results = cmp.evaluate_many(items, today=TODAY)

    assert len(results) == 3
    # 按调整后克单价升序
    assert results[0].item.name == "A 便宜低风险"
    assert results[1].item.name == "B 中等价"
    assert results[2].item.name == "C 最贵"
    # 最优应有推荐标签
    assert "推荐" in results[0].recommendation_label or "刷新" in results[0].recommendation_label
    # 最贵应不推荐
    assert "不推荐" in results[2].recommendation_label


# ========================================================================== #
# 验收标准 3：能记住历史低价
# 历史最低 0.038，新商品 0.036 → 提示刷新历史低价
# ========================================================================== #
def test_acceptance_3_remember_baseline():
    cmp = SnackComparator()
    # 先建立基线 0.038（19元 / 500g）
    cmp.evaluate(SnackItem(name="历史商品", total_price=19.0, total_weight_g=500,
                           flavor_type="fixed", expiry_date=TODAY + timedelta(days=60)), today=TODAY)
    assert abs(cmp.baseline_price_per_g - 0.038) < 1e-6

    # 新商品更便宜 0.036（18元 / 500g）
    r = cmp.evaluate(SnackItem(name="更便宜商品", total_price=18.0, total_weight_g=500,
                              flavor_type="fixed", expiry_date=TODAY + timedelta(days=60)), today=TODAY)
    assert r.baseline_updated is True, "应触发刷新历史低价"
    assert "刷新" in r.recommendation_label
    assert abs(cmp.baseline_price_per_g - 0.036) < 1e-6
    # 验收标准3：提示比之前低 5.26%
    saving = (0.038 - 0.036) / 0.038 * 100
    assert abs(saving - 5.26) < 0.01
    assert "5.26" in r.reason, f"reason 应包含降幅百分比，实际：{r.reason}"


# ========================================================================== #
# 边界与系数测试
# ========================================================================== #
def test_expired_item_not_recommended():
    item = SnackItem(name="过期", total_price=10, total_weight_g=200,
                    flavor_type="fixed", expiry_date=TODAY - timedelta(days=1))
    r = SnackComparator().evaluate(item, today=TODAY)
    assert r.risk_level == "已过期"
    assert "不推荐" in r.recommendation_label
    assert r.baseline_updated is False, "过期商品不应更新基线"


def test_flavor_preference_factors():
    cmp = SnackComparator(user_preference=UserPreference(
        preferred_flavors=["黑巧"], disliked_flavors=["辣味"], daily_intake_g=20))
    expiry = TODAY + timedelta(days=90)

    liked = cmp.evaluate(SnackItem(name="黑巧款", total_price=10, total_weight_g=200,
                                   flavor_type="fixed", flavor_name="黑巧", expiry_date=expiry), today=TODAY)
    disliked = cmp.evaluate(SnackItem(name="辣味款", total_price=10, total_weight_g=200,
                                      flavor_type="fixed", flavor_name="辣味", expiry_date=expiry), today=TODAY)
    neutral = cmp.evaluate(SnackItem(name="原味款", total_price=10, total_weight_g=200,
                                     flavor_type="fixed", flavor_name="原味", expiry_date=expiry), today=TODAY)

    assert abs(liked.flavor_factor - 0.95) < 1e-6
    assert abs(disliked.flavor_factor - 1.08) < 1e-6
    assert abs(neutral.flavor_factor - 1.00) < 1e-6


def test_expiry_risk_levels():
    cmp = SnackComparator(user_preference=UserPreference(daily_intake_g=20))
    # 500g / 20g每天 = 25天吃完
    # 低风险: 到期 > 50天 (ratio<0.5)
    low = cmp.evaluate(SnackItem(name="低", total_price=10, total_weight_g=500,
                                 flavor_type="fixed", expiry_date=TODAY + timedelta(days=100)), today=TODAY)
    # 中风险: 25/40 = 0.625
    mid = cmp.evaluate(SnackItem(name="中", total_price=10, total_weight_g=500,
                                 flavor_type="fixed", expiry_date=TODAY + timedelta(days=40)), today=TODAY)
    # 高风险: 25/20 = 1.25
    high = cmp.evaluate(SnackItem(name="高", total_price=10, total_weight_g=500,
                                  flavor_type="fixed", expiry_date=TODAY + timedelta(days=20)), today=TODAY)

    assert low.risk_level == "低风险"
    assert mid.risk_level == "中风险"
    assert high.risk_level == "高风险"
    assert abs(low.expiry_factor - 1.00) < 1e-6
    assert abs(mid.expiry_factor - 1.08) < 1e-6
    assert abs(high.expiry_factor - 1.20) < 1e-6


def test_unknown_expiry_factor():
    item = SnackItem(name="无日期", total_price=10, total_weight_g=200, flavor_type="fixed")
    r = SnackComparator().evaluate(item, today=TODAY)
    assert r.risk_level == "未知风险"
    assert abs(r.expiry_factor - 1.12) < 1e-6


def test_value_score_calculation():
    cmp = SnackComparator()
    # 建立基线
    cmp.evaluate(SnackItem(name="基线", total_price=20, total_weight_g=500,
                           flavor_type="fixed", expiry_date=TODAY + timedelta(days=90)), today=TODAY)
    # baseline = 0.04
    # 新商品 adjusted = 0.03 * 1.0 * 1.0 = 0.03
    r = cmp.evaluate(SnackItem(name="更优", total_price=15, total_weight_g=500,
                               flavor_type="fixed", expiry_date=TODAY + timedelta(days=90)), today=TODAY)
    # value_score = baseline / adjusted = 0.04 / 0.03 ≈ 1.333
    assert abs(r.value_score - (0.04 / 0.03)) < 1e-4


if __name__ == "__main__":
    # 简单运行器，无需 pytest 也能验证
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception:
            print(f"  ✗ {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} 通过")
    sys.exit(0 if passed == len(tests) else 1)
