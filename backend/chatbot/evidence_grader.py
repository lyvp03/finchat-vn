"""Evidence grader — assess data sufficiency before LLM synthesis."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger("evidence_grader")


@dataclass
class EvidenceGrade:
    """Assessment of available evidence for answering a causal question."""
    can_explain_cause: bool
    confidence: str                 # "high" | "medium" | "low"
    available_data: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    reason: str = ""


# ---------------------------------------------------------------
# Grading rules
# ---------------------------------------------------------------

_ALL_DATA_SOURCES = [
    "domestic_price",
    "xauusd",
    "usd_vnd",
    "direct_news",
    "contextual_news",
]


def grade_evidence(context: Dict[str, Any]) -> EvidenceGrade:
    """
    Grade evidence sufficiency based on what data is actually present.

    Rules:
      - SJC only                          → can_explain=False, confidence=low
      - SJC + contextual news             → can_explain=False, confidence=low
      - SJC + XAUUSD + USDVND            → can_explain=True,  confidence=medium
      - SJC + XAUUSD + USDVND + direct   → can_explain=True,  confidence=high
    """
    available: List[str] = []
    missing: List[str] = []

    # 1. Domestic price
    price = context.get("price")
    if price and price.get("ok"):
        available.append("domestic_price")
    else:
        missing.append("domestic_price")

    # 2. XAUUSD
    market = context.get("market") or {}
    xauusd = market.get("xauusd", {})
    if xauusd.get("ok"):
        available.append("xauusd")
    else:
        missing.append("xauusd")

    # 3. USDVND
    usdvnd = market.get("usdvnd", {})
    if usdvnd.get("ok"):
        available.append("usd_vnd")
    else:
        missing.append("usd_vnd")

    # 4. News classification
    news = context.get("news") or {}
    articles = news.get("articles", [])

    has_direct = False
    has_contextual = False
    for article in articles:
        tier = article.get("news_tier", "contextual")
        if tier == "direct":
            has_direct = True
        elif tier == "contextual":
            has_contextual = True

    if has_direct:
        available.append("direct_news")
    else:
        missing.append("direct_news")

    if has_contextual:
        available.append("contextual_news")

    # --- Apply grading rules ---
    has_market_trio = all(
        s in available for s in ("domestic_price", "xauusd", "usd_vnd")
    )

    if has_market_trio and has_direct:
        grade = EvidenceGrade(
            can_explain_cause=True,
            confidence="high",
            available_data=available,
            missing_data=missing,
            reason="Full evidence: domestic price, world market, and direct news available.",
        )
    elif has_market_trio:
        grade = EvidenceGrade(
            can_explain_cause=True,
            confidence="medium",
            available_data=available,
            missing_data=missing,
            reason="Market correlation available (SJC + XAUUSD + USDVND), but no direct news.",
        )
    elif "domestic_price" in available and (has_contextual or has_direct):
        grade = EvidenceGrade(
            can_explain_cause=False,
            confidence="low",
            available_data=available,
            missing_data=missing,
            reason="Only domestic price and contextual/direct news. Missing world market data for causal analysis.",
        )
    elif "domestic_price" in available:
        grade = EvidenceGrade(
            can_explain_cause=False,
            confidence="low",
            available_data=available,
            missing_data=missing,
            reason="Only domestic price available. Cannot explain causes.",
        )
    else:
        grade = EvidenceGrade(
            can_explain_cause=False,
            confidence="low",
            available_data=available,
            missing_data=missing,
            reason="Insufficient data.",
        )

    logger.info(
        "[EVIDENCE] can_explain=%s confidence=%s available=%s missing=%s",
        grade.can_explain_cause, grade.confidence, available, missing,
    )
    return grade


def format_evidence_for_prompt(grade: EvidenceGrade) -> str:
    """Format evidence grade as a context block for the LLM prompt."""
    lines = [
        f"Can explain cause: {'Yes' if grade.can_explain_cause else 'No'}",
        f"Confidence: {grade.confidence}",
        f"Available data: {', '.join(grade.available_data) or 'none'}",
        f"Missing data: {', '.join(grade.missing_data) or 'none'}",
    ]
    if not grade.can_explain_cause:
        lines.append(
            "INSTRUCTION: Do NOT assert causation. State that data is insufficient "
            "to determine the cause. Only describe what the data shows."
        )
    elif grade.confidence == "medium":
        lines.append(
            "INSTRUCTION: You may suggest possible correlations but use hedging language "
            '("có thể liên quan", "nhiều khả năng"). Do not assert definitive causation.'
        )
    return "\n".join(lines)
