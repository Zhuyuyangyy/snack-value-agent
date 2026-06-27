"""
Pure-Python rule-based outfit scorer.

Mirrors frontend/lib/rule-scorer.js (must stay in sync).
Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5.4
"""
from __future__ import annotations

from typing import Any


class ScorerError(ValueError):
    """Raised when input item is missing required fields."""


REQUIRED_FIELDS = ("id", "category", "slot", "price", "styleTags", "riskTags")


def _validate(items: list[dict[str, Any]]) -> None:
    for it in items:
        missing = [f for f in REQUIRED_FIELDS if f not in it]
        if missing:
            raise ScorerError(f"item {it.get('id', '?')!r} missing fields: {missing}")


def _layer_completeness(items: list[dict[str, Any]]) -> int:
    slots = {it["slot"] for it in items}
    has = lambda s: s in slots
    score = 0
    if has("upper"):
        score += 30
    if has("lower"):
        score += 30
    if has("feet"):
        score += 25
    if has("neck") or has("extra") or has("head"):
        score += 15
    return min(score, 100)


def _style_consistency(items: list[dict[str, Any]]) -> int:
    if len(items) < 2:
        return 0
    sets = [set(it["styleTags"]) for it in items]
    intersection = set.intersection(*sets) if sets else set()
    union = set.union(*sets) if sets else set()
    if not union or not intersection:
        return 0
    raw = (len(intersection) ** 2) / (len(union) * len(intersection))
    return min(int(raw * 100), 100)


def _color_harmony(items: list[dict[str, Any]]) -> int:
    distinct_colors = {t for it in items for t in it["styleTags"] if t.endswith("系")}
    n = len(distinct_colors)
    if n <= 1:
        return 100
    if n == 2:
        return 80
    if n == 3:
        return 60
    return 40


def _weighted_avg(items: list[dict[str, Any]], key: str) -> int:
    total_price = sum(it["price"] for it in items) or 1
    weighted = sum(it["price"] * it.get(key, 0) for it in items)
    return int(weighted / total_price)


def _risk_score(items: list[dict[str, Any]]) -> int:
    total_risks = sum(len(it["riskTags"]) for it in items)
    return max(0, 100 - total_risks * 15)


def _collect_tags(items: list[dict[str, Any]], key: str) -> list[str]:
    seen: list[str] = []
    for it in items:
        for t in it[key]:
            if t not in seen:
                seen.append(t)
    return seen


def score_outfit(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Score an outfit purely from item attributes. No LLM involved."""
    _validate(items)
    return {
        "scores": {
            "styleConsistency": _style_consistency(items),
            "colorHarmony": _color_harmony(items),
            "layerCompleteness": _layer_completeness(items),
            "photoScore": _weighted_avg(items, "photoScore"),
            "dailyScore": _weighted_avg(items, "dailyScore"),
            "riskScore": _risk_score(items),
        },
        "styleTags": _collect_tags(items, "styleTags"),
        "riskTags": _collect_tags(items, "riskTags"),
        "suggestion": "规则评分：未调用 AI。",
        "source": "rule-fallback",
    }