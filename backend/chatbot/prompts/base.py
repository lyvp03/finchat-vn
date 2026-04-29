"""Shared guardrails and utilities for all intent prompts."""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("prompts.guardrails")

# ---------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------

SHARED_FOOTER = "Always answer in Vietnamese. Be concise and data-driven."

INVESTMENT_ADVICE_PATTERNS = [
    r"\bmua ngay\b",
    r"\bbán ngay\b",
    r"\bnên mua\b",
    r"\bnên bán\b",
    r"\bkhuyên mua\b",
    r"\bkhuyên bán\b",
    r"\bnên đầu tư\b",
    r"\bbuy now\b",
    r"\bsell now\b",
]

INVESTMENT_ADVICE_DISCLAIMER = (
    "\n\n⚠️ Lưu ý: Đây là phân tích thông tin, không phải lời khuyên đầu tư."
)


# ---------------------------------------------------------------
# Guardrail runner
# ---------------------------------------------------------------

def apply_guardrails(response: str, intent: str) -> str:
    """
    Apply intent-specific guardrails to LLM response.

    Does NOT reject the response — instead appends disclaimers or
    warning notes so user still gets useful output.
    """
    # 1. Shared: detect & flag investment advice
    lower = response.lower()
    triggered = [p for p in INVESTMENT_ADVICE_PATTERNS if re.search(p, lower)]
    if triggered:
        logger.warning(
            "[GUARDRAIL] Investment advice detected in %s response: %s",
            intent, triggered,
        )
        response += INVESTMENT_ADVICE_DISCLAIMER

    # 2. price_sql: should not cite news sources
    if intent == "price_sql":
        news_source_hints = ["vnexpress", "cafef", "reuters", "kitco", "bloomberg", "tuoi tre"]
        mentioned = [s for s in news_source_hints if s in lower]
        if mentioned:
            logger.warning(
                "[GUARDRAIL] price_sql response mentions news sources: %s — no news context provided",
                mentioned,
            )

    # 3. news_rag: check that at least one source is cited
    if intent == "news_rag":
        has_citation = any(
            marker in lower
            for marker in ["nguồn:", "source:", "[1]", "[2]", "theo ", "from "]
        )
        if not has_citation:
            logger.warning("[GUARDRAIL] news_rag response has no source citation")

    # 4. hybrid: check 3-part structure
    if intent == "hybrid":
        has_price_section = any(k in lower for k in ["diễn biến giá", "price data", "giá vàng"])
        has_news_section = any(k in lower for k in ["tin tức", "news", "nguồn", "source"])
        has_summary = any(k in lower for k in ["nhận định", "tổng hợp", "summary", "kết luận"])
        if not (has_price_section and has_news_section and has_summary):
            logger.warning(
                "[GUARDRAIL] hybrid response missing sections: price=%s news=%s summary=%s",
                has_price_section, has_news_section, has_summary,
            )

    return response
