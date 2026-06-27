"""
LLM-based outfit advisor. Falls back to rule_scorer on any failure.

Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from . import rule_scorer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个"平价穿搭避坑分析师"。根据用户已选商品 + intent，输出严格 JSON。
suggestion 必须 ≤ 60 个中文字，不要 Markdown，不要代码块，不要任何 HTML/XML/LaTeX。
所有 scores 必须是 0-100 的整数。"""

INTENT_PROMPTS = {
    "cheaper": "用户想压低总价。请在 suggestion 中指出哪件单品可以用更便宜的同类替代。",
    "photo": "用户想拍照更出片。请在 suggestion 中给出提升视觉冲击的建议。",
    "daily": "用户想日常也好穿。请在 suggestion 中建议降低夸张程度。",
    "lower_risk": "用户想降低廉价感风险。请在 suggestion 中指出最显廉价的单品。",
    None: "用户未指定 intent。给出整体搭配评价和改进建议。",
}


# Sentinel: when set to None in tests, we skip LLM entirely.
_call_gemini = True


def _try_gemini(items: list[dict[str, Any]], intent: str | None) -> dict[str, Any] | None:
    if not _call_gemini:
        return None
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        logger.info("GEMINI_API_KEY not set, using rule fallback")
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        user_prompt = (
            f"intent: {intent or 'none'}\n"
            f"items: {json.dumps(items, ensure_ascii=False)}\n\n"
            f"{INTENT_PROMPTS.get(intent, INTENT_PROMPTS[None])}\n\n"
            "输出 JSON: {scores: {styleConsistency, colorHarmony, layerCompleteness, photoScore, dailyScore, riskScore}, styleTags: [..], riskTags: [..], suggestion: '..'}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.4,
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
                "timeout": 6.0,
            },
        )
        data = json.loads(response.text)
        _validate(data)
        data["source"] = "gemini-flash"
        return data
    except Exception as e:
        logger.warning(f"Gemini call failed, falling back to rule: {e}")
        return None


def _validate(data: dict[str, Any]) -> None:
    required_scores = {
        "styleConsistency", "colorHarmony", "layerCompleteness",
        "photoScore", "dailyScore", "riskScore",
    }
    if "scores" not in data:
        raise ValueError("missing scores")
    if set(data["scores"].keys()) != required_scores:
        raise ValueError("scores keys mismatch")
    for v in data["scores"].values():
        if not isinstance(v, (int, float)) or not (0 <= v <= 100):
            raise ValueError(f"score out of range: {v}")
    if "suggestion" not in data or len(data["suggestion"]) > 80:
        raise ValueError("suggestion missing or too long")


def get_advice(items: list[dict[str, Any]], intent: str | None = None) -> dict[str, Any]:
    """Public entry: try Gemini, fall back to rule scorer."""
    llm_result = _try_gemini(items, intent)
    if llm_result is not None:
        return llm_result
    return rule_scorer.score_outfit(items)
