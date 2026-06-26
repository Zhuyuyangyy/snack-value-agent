"""SnackItem Pydantic 模型字段校验。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import date
from pydantic import ValidationError

from backend.models import SnackItem


def test_minimal_required_fields():
    """最小必填字段：name + final_price + total_weight_g。"""
    item = SnackItem(name="测试", final_price=10.0, total_weight_g=100)
    assert item.name == "测试"
    assert item.final_price == 10.0
    assert item.total_weight_g == 100


def test_default_values():
    """默认值正确填充。"""
    item = SnackItem(name="X", final_price=10, total_weight_g=100)
    assert item.coupon_amount == 0
    assert item.discount_amount == 0
    assert item.shipping_fee == 0
    assert item.flavor_type == "unknown"
    assert item.package_type == "unknown"
    assert item.channel == "unknown"
    assert item.category == "unknown"
    assert item.after_opening_risk == "unknown"
    assert item.estimated_delivery_days == 3


def test_final_price_must_be_positive():
    """final_price 必须 > 0。"""
    with pytest.raises(ValidationError):
        SnackItem(name="X", final_price=0, total_weight_g=100)
    with pytest.raises(ValidationError):
        SnackItem(name="X", final_price=-1, total_weight_g=100)


def test_total_weight_g_must_be_positive():
    with pytest.raises(ValidationError):
        SnackItem(name="X", final_price=10, total_weight_g=0)


def test_flavor_type_4_categories():
    """flavor_type 必须是 4 选 1。"""
    for ft in ["fixed", "random", "mixed", "unknown"]:
        item = SnackItem(name="X", final_price=10, total_weight_g=100, flavor_type=ft)
        assert item.flavor_type == ft
    with pytest.raises(ValidationError):
        SnackItem(name="X", final_price=10, total_weight_g=100, flavor_type="invalid")


def test_package_type_enum():
    for pt in ["bag", "box", "bowl", "bottle", "can", "unknown"]:
        item = SnackItem(name="X", final_price=10, total_weight_g=100, package_type=pt)
        assert item.package_type == pt


def test_channel_enum():
    for ch in ["taobao", "tmall", "jd", "pdd", "douyin", "kuaishou", "offline", "unknown"]:
        item = SnackItem(name="X", final_price=10, total_weight_g=100, channel=ch)
        assert item.channel == ch


def test_category_enum():
    for cat in ["chocolate", "cookie", "chips", "candy", "beverage",
                "jerky", "cake", "nuts", "instant_food", "other", "unknown"]:
        item = SnackItem(name="X", final_price=10, total_weight_g=100, category=cat)
        assert item.category == cat


def test_after_opening_risk_enum():
    for r in ["low", "medium", "high", "unknown"]:
        item = SnackItem(name="X", final_price=10, total_weight_g=100, after_opening_risk=r)
        assert item.after_opening_risk == r


def test_expiry_date_iso_format():
    item = SnackItem(name="X", final_price=10, total_weight_g=100,
                     expiry_date=date(2026, 9, 1))
    assert item.expiry_date == date(2026, 9, 1)


def test_estimated_delivery_days_range():
    """estimated_delivery_days 在 [0, 30]。"""
    item = SnackItem(name="X", final_price=10, total_weight_g=100,
                     estimated_delivery_days=0)
    assert item.estimated_delivery_days == 0
    item = SnackItem(name="X", final_price=10, total_weight_g=100,
                     estimated_delivery_days=30)
    assert item.estimated_delivery_days == 30
    with pytest.raises(ValidationError):
        SnackItem(name="X", final_price=10, total_weight_g=100, estimated_delivery_days=31)


def test_optional_fields_optional():
    """可选字段不传 = None。"""
    item = SnackItem(name="X", final_price=10, total_weight_g=100)
    assert item.listed_price is None
    assert item.single_weight_g is None
    assert item.quantity is None
    assert item.flavor_name is None
    assert item.expiry_date is None
    assert item.brand is None
    assert item.source_text is None
    assert item.source_url is None


def test_name_cannot_be_empty():
    with pytest.raises(ValidationError):
        SnackItem(name="   ", final_price=10, total_weight_g=100)


def test_backfill_total_price():
    """向后兼容：仅传 total_price 时，自动同步给 final_price。"""
    item = SnackItem(name="X", total_price=10, total_weight_g=100)
    assert item.final_price == 10
    assert item.total_price == 10


def test_backfill_total_price_prefers_explicit_final_price():
    """final_price 显式传值时优先使用，不被 total_price 覆盖。"""
    item = SnackItem(name="X", final_price=20, total_price=10, total_weight_g=100)
    assert item.final_price == 20
    assert item.total_price == 10


def test_field_confidences_must_be_in_range():
    """field_confidences 值必须在 [0, 1]。"""
    with pytest.raises(ValidationError):
        SnackItem(name="X", final_price=10, total_weight_g=100,
                  field_confidences={"price": 1.5})


def test_field_confidences_valid():
    """合法 field_confidences 接受。"""
    item = SnackItem(name="X", final_price=10, total_weight_g=100,
                    field_confidences={"price": 0.95, "weight": 0.8})
    assert item.field_confidences["price"] == 0.95


def test_field_confidences_none_allowed():
    item = SnackItem(name="X", final_price=10, total_weight_g=100)
    assert item.field_confidences is None
