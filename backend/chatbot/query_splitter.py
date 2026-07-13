"""Split multi-topic user questions and classify scope (gold market vs out-of-scope).

Single LLM call performs both split AND scope classification.
Fail-open: if LLM fails, treat entire question as in-scope (let pipeline handle it).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger("query_splitter")


# ---------------------------------------------------------------
# Prompt — combined split + classify in one call
# ---------------------------------------------------------------

SPLIT_AND_CLASSIFY_PROMPT = """You are a query analyzer for a GOLD MARKET chatbot.

TASK: Analyze the user's message and do TWO things:
1. SPLIT: If the message contains multiple INDEPENDENT topics (unrelated to each other),
   split into separate sub-questions. If there is only ONE topic (even if long), keep it as-is.
2. CLASSIFY SCOPE: For each sub-question, determine if it is about gold market topics.

In-scope topics: gold prices (SJC, DOJI, XAUUSD), gold market news, gold price analysis,
technical indicators for gold (RSI/EMA/MACD), domestic-world premium comparison,
factors affecting gold prices (Fed, USD, inflation, geopolitics).

Out-of-scope topics: algorithms, programming, food, crypto, stocks, general knowledge,
anything unrelated to gold market.

User message: {question}

Return ONLY valid JSON, no explanation:
{{"sub_questions": [
  {{"text": "...", "in_scope": true, "reason": "..."}},
  ...
]}}"""


# ---------------------------------------------------------------
# Data model
# ---------------------------------------------------------------

@dataclass(frozen=True)
class SubQuestion:
    text: str
    in_scope: bool
    reason: str


# ---------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------

def _strip_json_fence(text: str) -> str:
    """Remove ```json fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return text


def split_and_classify(question: str, llm_client) -> list[SubQuestion]:
    """
    Split question into sub-questions and classify each as in/out-of-scope.

    Uses a single LLM call for both operations.
    Fail-open: returns [SubQuestion(original, in_scope=True)] on any error.
    """
    fallback = [SubQuestion(text=question, in_scope=True, reason="single_or_fallback")]

    try:
        raw = llm_client.generate(
            [{"role": "user", "content": SPLIT_AND_CLASSIFY_PROMPT.format(question=question)}],
            temperature=0.0,
        )
        if not raw or not raw.strip():
            logger.warning("[SPLIT] LLM returned empty response, using fallback")
            return fallback

        cleaned = _strip_json_fence(raw)
        parsed = json.loads(cleaned)

        items = parsed.get("sub_questions", [])
        if not items or not isinstance(items, list):
            logger.warning("[SPLIT] Invalid structure from LLM, using fallback")
            return fallback

        result = []
        for item in items:
            if not isinstance(item, dict) or "text" not in item:
                continue
            result.append(SubQuestion(
                text=item["text"].strip(),
                in_scope=bool(item.get("in_scope", True)),  # fail-open
                reason=str(item.get("reason", "")),
            ))

        if not result:
            return fallback

        logger.info(
            "[SPLIT] %d sub-questions: %s",
            len(result),
            [(sq.text[:40], sq.in_scope) for sq in result],
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning("[SPLIT] JSON parse error: %s. Raw: %r", e, raw[:200] if raw else "")
        return fallback
    except Exception:
        logger.exception("[SPLIT] Failed to split/classify, using fallback")
        return fallback


# ---------------------------------------------------------------
# Response merger
# ---------------------------------------------------------------

OUT_OF_SCOPE_TEMPLATE = (
    'Về phần "{question}" — nội dung này nằm ngoài phạm vi tư vấn giá vàng của tôi, '
    "nên tôi không thể trả lời chính xác được. Bạn có thể tìm hiểu thêm qua các nguồn "
    "chuyên về chủ đề đó nhé."
)


def merge_responses(
    sections: list[dict],
    sub_questions: list[SubQuestion],
) -> dict:
    """Merge responses from multiple sub-questions into one coherent response."""
    parts = []
    intents = []

    for section, sq in zip(sections, sub_questions):
        if len(sections) > 1:
            # Prefix each section with the sub-question as header
            parts.append(f"**{sq.text}**\n\n{section['response']}")
        else:
            parts.append(section["response"])
        intents.append(section.get("intent", "unknown"))

    return {
        "response": "\n\n---\n\n".join(parts),
        "intent": "multi_intent",
        "sub_intents": intents,
        "sources": {"sub_questions": [sq.text for sq in sub_questions]},
    }
