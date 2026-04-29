"""Main chatbot flow."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from chatbot.context_builder import build_context
from chatbot.context_compressor import compact_news_context, format_price_context
from chatbot.evidence_grader import grade_evidence, format_evidence_for_prompt
from chatbot.prompts import build_answer_messages, run_guardrails
from chatbot.router import analyze_question
from core.llm.factory import get_llm_client

logger = logging.getLogger("orchestrator")


def answer_question(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Luồng chính: question → route → context → LLM → response.

    Returns:
        {response, intent, sources}
    """
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info("[FLOW 1/5] QUESTION: %r", question[:120])

    route = analyze_question(question)
    intent = route.intent
    logger.info(
        "[FLOW 2/5] INTENT: %s (confidence=%.2f) | reason: %s",
        intent, route.confidence, route.reason,
    )

    # Out-of-scope → trả lời luôn, không gọi tools hay LLM
    if intent == "general":
        logger.info("[FLOW] OUT-OF-SCOPE → returning static response")
        return {
            "response": "Câu hỏi này nằm ngoài phạm vi dữ liệu giá vàng và tin tức vàng hiện có.",
            "intent": intent,
            "sources": {"price": None, "news": None, "errors": [], "route": route.__dict__},
        }

    # Gọi tools lấy data
    logger.info("[FLOW 3/5] FETCHING CONTEXT (tools)...")
    context = build_context(question, intent)
    context["route"] = route.__dict__

    has_price = context.get("price") and context["price"].get("ok")
    has_news = context.get("news") and context["news"].get("count", 0) > 0
    has_market = context.get("market") is not None
    has_premium = context.get("premium") is not None
    logger.info(
        "[FLOW 3/5] CONTEXT READY: has_price=%s has_market=%s has_premium=%s has_news=%s "
        "news_count=%s errors=%s",
        has_price, has_market, has_premium, has_news,
        (context.get("news") or {}).get("count", 0),
        context.get("errors"),
    )

    # Evidence grading — determines if LLM may assert causation
    evidence = grade_evidence(context)
    context["evidence_grade"] = {
        "can_explain_cause": evidence.can_explain_cause,
        "confidence": evidence.confidence,
        "available_data": evidence.available_data,
        "missing_data": evidence.missing_data,
        "reason": evidence.reason,
    }
    context["evidence_prompt"] = format_evidence_for_prompt(evidence)
    logger.info(
        "[FLOW 3.5/5] EVIDENCE: can_explain=%s confidence=%s",
        evidence.can_explain_cause, evidence.confidence,
    )

    # Nếu không có dữ liệu gì cả → không cần gọi LLM
    if not has_price and not has_news and context.get("errors"):
        logger.warning("[FLOW] NO DATA → skipping LLM, returning error response")
        return {
            "response": (
                "Hiện chưa truy vấn được dữ liệu để trả lời chính xác.\n"
                f"Lỗi: {'; '.join(context['errors'])}\n"
                "Vui lòng kiểm tra ClickHouse / Qdrant / Ollama."
            ),
            "intent": intent,
            "sources": context,
        }

    # Build prompt và gọi LLM
    logger.info("[FLOW 4/5] BUILDING PROMPT...")
    messages = build_answer_messages(question, context, intent=intent, history=history)
    total_chars = sum(len(m.get("content", "")) for m in messages)
    logger.info(
        "[FLOW 4/5] PROMPT READY: intent=%s messages=%d total_chars=%d",
        intent, len(messages), total_chars,
    )

    logger.info("[FLOW 5/5] CALLING LLM (model via factory)...")
    try:
        response = get_llm_client().generate(messages)
        elapsed = time.perf_counter() - t0
        logger.info(
            "[FLOW 5/5] LLM SUCCESS: total_latency=%.2fs response_chars=%d",
            elapsed, len(response),
        )
        response = run_guardrails(response, intent)
    except Exception as exc:
        logger.error("[FLOW 5/5] LLM FAILED: %s — using fallback", exc, exc_info=True)
        response = _fallback_answer(intent, context, exc)

    return {"response": response, "intent": intent, "sources": context}


def _fallback_answer(intent: str, context: Dict[str, Any], exc: Exception) -> str:
    """Tạo câu trả lời readable khi LLM không gọi được."""
    logger.warning("Generating fallback answer due to LLM error: %s", type(exc).__name__)
    parts = [
        f"⚠️ Không gọi được LLM ({type(exc).__name__}). "
        "Dưới đây là dữ liệu thô truy vấn được:\n"
    ]

    price = context.get("price")
    if intent in ("price_sql", "hybrid") and price:
        parts.append("--- Dữ liệu giá ---")
        parts.append(format_price_context(price))

    news = context.get("news")
    if intent in ("news_rag", "hybrid") and news and news.get("articles"):
        articles = news["articles"][:3]
        time_note = news.get("time_filter_note", "")
        if time_note:
            parts.append(f"\n⚠️ {time_note}")
        parts.append("\n--- Tin tức tìm được ---")
        for i, article in enumerate(articles, 1):
            published = (article.get("published_at") or "")[:10]
            parts.append(
                f"{i}. {article.get('title', 'N/A')} "
                f"- {article.get('source_name', '')} "
                f"- {published}"
            )

    if len(parts) == 1:
        parts.append("(Không có dữ liệu price hay news để hiển thị.)")

    return "\n".join(parts)
