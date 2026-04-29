"""Prompt package — public API for building LLM messages."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from chatbot.context_compressor import compact_news_context, format_price_context
from chatbot.prompts.base import apply_guardrails
from chatbot.prompts.hybrid_prompt import HYBRID_SYSTEM_PROMPT
from chatbot.prompts.news_prompt import NEWS_SYSTEM_PROMPT
from chatbot.prompts.price_prompt import PRICE_SYSTEM_PROMPT

logger = logging.getLogger("prompts")

# Map intent → system prompt
_SYSTEM_PROMPTS: Dict[str, str] = {
    "price_sql": PRICE_SYSTEM_PROMPT,
    "news_rag": NEWS_SYSTEM_PROMPT,
    "hybrid": HYBRID_SYSTEM_PROMPT,
}


def build_answer_messages(
    question: str,
    context: Dict[str, Any],
    intent: str,
    history: List[Dict[str, str]] | None = None,
) -> List[Dict[str, str]]:
    """
    Build message list for the LLM.

    - System prompt is chosen per intent (price / news / hybrid).
    - Context only contains data relevant to the intent:
        price_sql  → price only
        news_rag   → news only
        hybrid     → price + news
    """
    system_prompt = _SYSTEM_PROMPTS.get(intent, HYBRID_SYSTEM_PROMPT)
    context_str = _build_context_string(context, intent)

    errors = context.get("errors", [])
    if errors:
        context_str += f"\n\n[SYSTEM NOTE: Some data sources had errors: {'; '.join(errors)}]"

    price_chars = len(format_price_context(context.get("price"))) if context.get("price") else 0
    articles = (context.get("news") or {}).get("articles", [])
    logger.info(
        "[PROMPTS] intent=%s system_chars=%d price_chars=%d news_articles=%d context_chars=%d",
        intent, len(system_prompt), price_chars, len(articles), len(context_str),
    )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        # Filter: Ollama rejects messages without role/content or with empty content
        valid_roles = {"user", "assistant", "system"}
        valid_history = [
            msg for msg in history[-6:]
            if isinstance(msg, dict)
            and msg.get("role") in valid_roles
            and msg.get("content", "").strip()
        ]
        skipped = len(history[-6:]) - len(valid_history)
        if skipped:
            logger.warning(
                "[PROMPTS] Filtered %d invalid history messages (empty content or bad role)",
                skipped,
            )
        messages.extend(valid_history)

    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context_str}\n\nQUESTION: {question}",
    })
    return messages


def run_guardrails(response: str, intent: str) -> str:
    """Apply intent-specific guardrails to LLM response. Re-exported for orchestrator."""
    return apply_guardrails(response, intent)


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------

def _build_context_string(context: Dict[str, Any], intent: str) -> str:
    """Only include context sections relevant to the intent."""
    parts: List[str] = []

    if intent in ("price_sql", "hybrid"):
        price_text = format_price_context(context.get("price"))
        parts.append(f"=== PRICE DATA ===\n{price_text}")

    # Market data (XAUUSD + USDVND) — only for hybrid
    if intent == "hybrid":
        market = context.get("market")
        if market:
            market_lines = []
            for sym in ("xauusd", "usdvnd"):
                data = market.get(sym, {})
                if data.get("ok"):
                    latest = data.get("latest", {})
                    market_lines.append(
                        f"{data['symbol']}: {latest.get('price', '?')} "
                        f"| trend: {data.get('trend', '?')} | change: {data.get('change', '?')} "
                        f"({data.get('change_pct', '?')}%) | period: {data.get('from')}→{data.get('to')}"
                    )
                else:
                    market_lines.append(f"{sym.upper()}: (no data)")
            parts.append(f"=== WORLD MARKET DATA ===\n" + "\n".join(market_lines))

        premium = context.get("premium")
        if premium and premium.get("ok"):
            parts.append(
                f"=== DOMESTIC-WORLD PREMIUM ===\n"
                f"World gold (VND/lượng): {premium['world_gold_vnd_per_luong']:,.0f}\n"
                f"Premium: {premium['premium']:+,.0f} VND ({premium['premium_pct']:+.2f}%)"
            )

    if intent in ("news_rag", "hybrid"):
        articles = (context.get("news") or {}).get("articles", [])
        time_note = (context.get("news") or {}).get("time_filter_note", "")
        news_text = compact_news_context(articles)
        if time_note:
            news_text = f"[NOTE] {time_note}\n\n{news_text}"
        parts.append(f"=== NEWS EVIDENCE ===\n{news_text}")

    # Evidence grade — tells LLM what it's allowed to conclude
    evidence_prompt = context.get("evidence_prompt")
    if evidence_prompt:
        parts.append(f"=== EVIDENCE ASSESSMENT ===\n{evidence_prompt}")

    return "\n\n".join(parts) if parts else "(No context data available)"
