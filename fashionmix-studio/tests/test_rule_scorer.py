import pytest

from backend.rule_scorer import score_outfit, ScorerError


def _item(item_id, category, slot, style_tags, risk_tags, price, photo=70, daily=70, quality=70):
    return {
        "id": item_id,
        "category": category,
        "slot": slot,
        "price": price,
        "styleTags": style_tags,
        "riskTags": risk_tags,
        "photoScore": photo,
        "dailyScore": daily,
        "qualityScore": quality,
    }


def test_empty_outfit_returns_low_layer_score():
    result = score_outfit([])
    assert result["scores"]["layerCompleteness"] == 0
    assert result["scores"]["styleConsistency"] == 0
    assert result["source"] == "rule-fallback"


def test_full_match_layer_completeness_is_100():
    items = [
        _item("top1", "top", "upper", ["学院"], [], 30),
        _item("skirt1", "skirt", "lower", ["学院"], [], 40),
        _item("shoe1", "shoes", "feet", ["学院"], [], 50),
        _item("acc1", "accessory", "neck", ["学院"], [], 10),
    ]
    result = score_outfit(items)
    assert result["scores"]["layerCompleteness"] == 100


def test_style_consistency_full_overlap_is_100():
    items = [
        _item("a", "top", "upper", ["学院", "王子系"], [], 30),
        _item("b", "skirt", "lower", ["学院", "王子系"], [], 40),
    ]
    result = score_outfit(items)
    assert result["scores"]["styleConsistency"] == 100


def test_style_consistency_no_overlap_is_0():
    items = [
        _item("a", "top", "upper", ["哥特"], [], 30),
        _item("b", "skirt", "lower", ["学院"], [], 40),
    ]
    result = score_outfit(items)
    assert result["scores"]["styleConsistency"] == 0


def test_color_harmony_single_color_score_100():
    items = [
        _item("a", "top", "upper", ["黑色系"], [], 30),
        _item("b", "skirt", "lower", ["黑色系"], [], 40),
    ]
    result = score_outfit(items)
    assert result["scores"]["colorHarmony"] == 100


def test_risk_score_drops_with_more_risk_tags():
    no_risk = score_outfit([_item("a", "top", "upper", [], [], 30)])
    some_risk = score_outfit([_item("a", "top", "upper", [], ["偏短", "易皱"], 30)])
    assert some_risk["scores"]["riskScore"] < no_risk["scores"]["riskScore"]


def test_all_scores_in_0_100_range():
    items = [
        _item("a", "top", "upper", ["古早", "棕色系"], ["偏短", "起球"], 30, photo=80, daily=40),
        _item("b", "skirt", "lower", ["古早", "棕色系"], ["材质不确定"], 40, photo=85, daily=45),
    ]
    result = score_outfit(items)
    for v in result["scores"].values():
        assert 0 <= v <= 100


def test_photo_score_is_price_weighted_average():
    items = [
        _item("cheap", "top", "upper", [], [], 10, photo=50),
        _item("expensive", "skirt", "lower", [], [], 90, photo=100),
    ]
    result = score_outfit(items)
    # weighted: (10*50 + 90*100) / (10+90) = 95
    assert result["scores"]["photoScore"] == 95


def test_invalid_item_missing_field_raises():
    with pytest.raises(ScorerError):
        score_outfit([{"id": "x"}])  # missing required fields