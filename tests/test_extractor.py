"""V0.2 字段提取器测试：覆盖 8 类真实商品截图文本场景。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.extractor import extract_fields_from_text


def test_basic_price_and_weight():
    """场景1：价格清楚、重量清楚。"""
    text = "奥利奥薄脆 到手价19.9元 净含量500g"
    f = extract_fields_from_text(text)
    assert f.total_price.value == "19.90", f"价格应为 19.90，实际 {f.total_price.value}"
    assert f.total_price.confidence == "high"
    assert f.total_weight_g.value == "500", f"重量应为 500，实际 {f.total_weight_g.value}"
    assert f.total_weight_g.confidence == "high"


def test_coupon_price():
    """场景2：有券后价/满减价。"""
    text = "乐事薯片 原价29.9 券后价15.9元 净含量300g"
    f = extract_fields_from_text(text)
    # 券后价应优先
    assert f.total_price.value == "15.90", f"应取券后价 15.90，实际 {f.total_price.value}"
    assert f.total_weight_g.value == "300"


def test_multi_spec():
    """场景3：多规格混在一起。"""
    text = "三只松鼠坚果 84g×5袋 ¥39.9"
    f = extract_fields_from_text(text)
    assert f.total_weight_g.value == "420", f"84×5=420，实际 {f.total_weight_g.value}"
    assert f.total_price.value == "39.90"


def test_random_flavor():
    """场景4：随机口味/混发。"""
    text = "良品铺子零食大礼包 随机混发 ¥29.9 净含量800g"
    f = extract_fields_from_text(text)
    assert f.flavor_type.value == "random"
    assert f.flavor_type.confidence == "medium"


def test_expiry_date_clear():
    """场景5：到期日明显。"""
    text = "百草味坚果 保质期至2026年09月01日 ¥25.9 500g"
    f = extract_fields_from_text(text)
    assert f.expiry_date.value == "2026-09-01", f"到期日应为 2026-09-01，实际 {f.expiry_date.value}"
    assert f.expiry_date.confidence == "high"


def test_expiry_date_unclear():
    """场景6：到期日不明显（纯日期无上下文）。"""
    text = "旺旺雪饼 2026/08/15 ¥12.9 250g"
    f = extract_fields_from_text(text)
    assert f.expiry_date.value == "2026-08-15"
    assert f.expiry_date.confidence == "medium"  # 无"到期"关键词，中置信


def test_weight_compound():
    """场景7：重量写成 84g×5袋。"""
    text = "每日坚果 84g×5袋 到手价49.9元"
    f = extract_fields_from_text(text)
    assert f.total_weight_g.value == "420"
    assert f.quantity.value == "5", f"数量应为 5，实际 {f.quantity.value}"


def test_weight_net_content():
    """场景8：重量写成 净含量420g。"""
    text = "奥利奥 净含量420g ¥18.8"
    f = extract_fields_from_text(text)
    assert f.total_weight_g.value == "420"


def test_yuan_symbol_price():
    """价格带 ¥ 符号。"""
    text = "薯片 ¥9.9 150g"
    f = extract_fields_from_text(text)
    assert f.total_price.value == "9.90"


def test_kg_weight():
    """重量单位为 kg。"""
    text = "大米 净含量5kg ¥29.9"
    f = extract_fields_from_text(text)
    assert f.total_weight_g.value == "5000", f"5kg=5000g，实际 {f.total_weight_g.value}"


def test_fixed_flavor():
    """固定口味。"""
    text = "奥利奥原味 指定口味 ¥15.9 300g"
    f = extract_fields_from_text(text)
    assert f.flavor_type.value == "fixed"


def test_package_type():
    """包装类型。"""
    text = "坚果礼盒 ¥99 500g"
    f = extract_fields_from_text(text)
    assert f.package_type.value == "box"


def test_no_fields():
    """无任何可提取字段。"""
    text = "这是一段无关文字"
    f = extract_fields_from_text(text)
    assert f.total_price.confidence == "low"
    assert f.total_weight_g.confidence == "low"


def test_full_scenario():
    """完整真实场景：模拟电商截图 OCR 文本。"""
    text = """
    奥利奥薄脆饼干
    随机口味混发
    到手价 ¥19.9
    净含量500g
    保质期至2026年09月01日
    5袋装
    """
    f = extract_fields_from_text(text)
    assert f.total_price.value == "19.90"
    assert f.total_weight_g.value == "500"
    assert f.flavor_type.value == "random"
    assert f.expiry_date.value == "2026-09-01"
    assert f.quantity.value == "5"
    assert f.package_type.value == "bag"


if __name__ == "__main__":
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
