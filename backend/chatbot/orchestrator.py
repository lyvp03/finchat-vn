"""Main chatbot flow."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from chatbot.context_builder import build_context
from chatbot.context_compressor import compact_news_context, format_price_context
from chatbot.evidence_grader import grade_evidence, format_evidence_for_prompt
from chatbot.input_guardrail import check_input
from chatbot.prompts import build_answer_messages, run_guardrails
from chatbot.prompts.base import GuardrailViolation
from chatbot.query_splitter import (
    OUT_OF_SCOPE_TEMPLATE,
    SubQuestion,
    merge_responses,
    split_and_classify,
)
from chatbot.router import analyze_question_with_history
from core.llm.factory import get_llm_client
from core.config import settings

logger = logging.getLogger("orchestrator")

def _count_tokens_heuristic(text: str) -> int:
    """Heuristic: 1 token ≈ 4 characters."""
    if not text:
        return 0
    return max(1, len(text) // 4)

def _summarize_history_if_needed(history: list[dict] | None) -> tuple[list[dict], int]:
    if not history:
        return [], 0
    
    valid_roles = {"user", "assistant", "system"}
    valid_history = [
        msg for msg in history
        if isinstance(msg, dict)
        and msg.get("role") in valid_roles
        and msg.get("content", "").strip()
    ]
    
    if len(valid_history) > 6:
        old_turns = valid_history[:-6]
        recent_turns = valid_history[-6:]
        
        old_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in old_turns])
        prompt = (
            "Bạn là trợ lý AI phân tích thị trường vàng.\n"
            "Hãy tóm tắt thật ngắn gọn (1-2 câu) những mốc thời gian, loại vàng, hoặc sự kiện mà người dùng đã đề cập trong các lượt hỏi cũ để làm ngữ cảnh.\n\n"
            f"LỊCH SỬ CŨ:\n{old_str}"
        )
        try:
            summary = get_llm_client().generate([{"role": "user", "content": prompt}])
            logger.info("[HISTORY] Summarized %d old turns into %d chars", len(old_turns), len(summary))
        except Exception as e:
            logger.error("[HISTORY] Summarization failed: %s", e)
            summary = "Không thể tóm tắt lịch sử cũ."
            
        summary_msg = {"role": "system", "content": f"Tóm tắt hội thoại trước: {summary}"}
        new_history = [summary_msg] + recent_turns
    else:
        new_history = valid_history
        
    history_text = "".join(m.get("content", "") for m in new_history)
    history_tokens = _count_tokens_heuristic(history_text)
    
    return new_history, history_tokens

def _allocate_budget(intent: str, history_tokens: int) -> dict[str, int]:
    remaining_tokens = settings.TOTAL_CONTEXT_BUDGET - history_tokens
    if remaining_tokens < 1000:
        remaining_tokens = 1000 # Floor
        
    if intent == "hybrid":
        budget = {"price": int(remaining_tokens * 0.3), "news": int(remaining_tokens * 0.6), "buffer": int(remaining_tokens * 0.1)}
    elif intent == "news_rag":
        budget = {"price": 0, "news": int(remaining_tokens * 0.9), "buffer": int(remaining_tokens * 0.1)}
    else:
        budget = {"price": int(remaining_tokens * 0.5), "news": 0, "buffer": int(remaining_tokens * 0.5)}
    
    return {k: v * 4 for k, v in budget.items()} # Convert to chars


def answer_question(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Main flow: question -> split -> route -> context -> LLM -> response.

    Supports multi-intent: if user asks multiple unrelated questions,
    each is processed independently (in-scope through full pipeline,
    out-of-scope gets static rejection).
    """
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info("[FLOW 1/6] QUESTION: %r", question[:120])

    # ── Input guardrail ──
    input_check = check_input(question)
    injection_detected = False
    if not input_check.is_safe:
        if input_check.reason == "prompt_injection":
            logger.warning("[FLOW] INPUT GUARDRAIL DETECTED INJECTION. Overriding question.")
            injection_detected = True
            question = "Hãy phân tích tình hình giá vàng và thị trường hiện tại."
        else:
            logger.warning("[FLOW] INPUT BLOCKED: reason=%s", input_check.reason)
            return {
                "response": "Xin lỗi, câu hỏi này không thể xử lý được.",
                "intent": "blocked",
                "sources": {"block_reason": input_check.reason},
            }

    # ── Split + classify scope ──
    logger.info("[FLOW 2/6] SPLIT + CLASSIFY...")
    sub_questions = split_and_classify(question, get_llm_client())

    # Single in-scope question → standard pipeline
    if len(sub_questions) == 1 and sub_questions[0].in_scope:
        logger.info("[FLOW 2/6] Single in-scope question, proceeding normally")
        result = _answer_single(sub_questions[0].text, history, t0)
        if injection_detected:
            result["response"] += (
                "\n\n🚨 **LƯU Ý**: Hệ thống phát hiện thông tin bạn cung cấp có chứa yêu cầu "
                "bỏ qua dữ liệu hệ thống hoặc cung cấp số liệu không xác thực. Vui lòng không cung cấp "
                "thông tin giả mạo (fake news). Phân tích trên được thực hiện hoàn toàn dựa trên "
                "dữ liệu thật của thị trường."
            )
        return result

    # Single out-of-scope question → static rejection
    if len(sub_questions) == 1 and not sub_questions[0].in_scope:
        logger.info("[FLOW 2/6] Single out-of-scope: reason=%s", sub_questions[0].reason)
        result = {
            "response": OUT_OF_SCOPE_TEMPLATE.format(question=question),
            "intent": "out_of_scope",
            "sources": {"scope_reason": sub_questions[0].reason},
        }
        if injection_detected:
            result["response"] += (
                "\n\n🚨 **LƯU Ý**: Hệ thống phát hiện thông tin bạn cung cấp có chứa yêu cầu "
                "bỏ qua dữ liệu hệ thống hoặc cung cấp số liệu không xác thực. Vui lòng không cung cấp "
                "thông tin giả mạo (fake news). Phân tích trên được thực hiện hoàn toàn dựa trên "
                "dữ liệu thật của thị trường."
            )
        return result

    # Multi-intent → process each sub-question independently
    logger.info(
        "[FLOW 2/6] MULTI-INTENT: %d sub-questions: %s",
        len(sub_questions),
        [(sq.text[:40], "in" if sq.in_scope else "out") for sq in sub_questions],
    )

    sections: List[Dict[str, Any]] = []
    for i, sq in enumerate(sub_questions, 1):
        if not sq.in_scope:
            logger.info("[MULTI %d/%d] Out-of-scope: %r", i, len(sub_questions), sq.text[:50])
            sections.append({
                "response": OUT_OF_SCOPE_TEMPLATE.format(question=sq.text),
                "intent": "out_of_scope",
            })
            continue

        logger.info("[MULTI %d/%d] In-scope, running full pipeline: %r", i, len(sub_questions), sq.text[:50])
        result = _answer_single(sq.text, history, t0)
        sections.append(result)

    elapsed = time.perf_counter() - t0
    merged = merge_responses(sections, sub_questions)
    logger.info("[FLOW 6/6] MULTI-INTENT DONE: %d sections, total=%.2fs", len(sections), elapsed)
    
    if injection_detected:
        merged["response"] += (
            "\n\n🚨 **LƯU Ý**: Hệ thống phát hiện thông tin bạn cung cấp có chứa yêu cầu "
            "bỏ qua dữ liệu hệ thống hoặc cung cấp số liệu không xác thực. Vui lòng không cung cấp "
            "thông tin giả mạo (fake news). Phân tích trên được thực hiện hoàn toàn dựa trên "
            "dữ liệu thật của thị trường."
        )

    return merged


def _answer_single(
    question: str,
    history: Optional[List[Dict[str, str]]],
    t0: float,
) -> Dict[str, Any]:
    """Handle exactly one in-scope sub-question."""
    new_history, history_tokens = _summarize_history_if_needed(history)
    logger.info("[FLOW 3/6] ANALYZING INTENT...")
    route = analyze_question_with_history(question, new_history)
    intent = route.intent
    
    budget_chars = _allocate_budget(intent, history_tokens)
    logger.info(
        "[FLOW 3/6] INTENT: %s (confidence=%.2f) | reason: %s | budget_chars: %s",
        intent, route.confidence, route.reason, budget_chars,
    )

    if intent == "out_of_scope":
        return {
            "response": OUT_OF_SCOPE_TEMPLATE.format(question=question),
            "intent": "out_of_scope",
            "sources": {"route_reason": route.reason},
        }

    # Fetch context via tools
    logger.info("[FLOW 4/6] FETCHING CONTEXT (tools)...")
    context = build_context(question, intent, budget_chars=budget_chars)
    context["route"] = route.__dict__

    has_price = context.get("price") and context["price"].get("ok")
    has_news = context.get("news") and context["news"].get("count", 0) > 0
    has_market = context.get("market") is not None
    has_premium = context.get("premium") is not None
    logger.info(
        "[FLOW 4/6] CONTEXT READY: has_price=%s has_market=%s has_premium=%s has_news=%s "
        "news_count=%s errors=%s",
        has_price, has_market, has_premium, has_news,
        (context.get("news") or {}).get("count", 0),
        context.get("errors"),
    )

    # Evidence grading
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
        "[FLOW 4.5/6] EVIDENCE: can_explain=%s confidence=%s",
        evidence.can_explain_cause, evidence.confidence,
    )

    # No data at all → skip LLM
    if not has_price and not has_news and context.get("errors"):
        logger.warning("[FLOW] NO DATA → skipping LLM, returning error response")
        return {
            "response": (
                "Xin lỗi, hiện tại hệ thống chưa truy vấn được dữ liệu.\n"
                "Vui lòng thử lại sau hoặc đặt câu hỏi khác."
            ),
            "intent": intent,
            "sources": context,
        }

    # Build prompt and call LLM
    logger.info("[FLOW 5/6] BUILDING PROMPT...")
    messages = build_answer_messages(question, context, intent=intent, history=new_history, budget_chars=budget_chars)
    total_chars = sum(len(m.get("content", "")) for m in messages)
    logger.info(
        "[FLOW 5/6] PROMPT READY: intent=%s messages=%d total_chars=%d",
        intent, len(messages), total_chars,
    )

    logger.info("[FLOW 6/6] CALLING LLM (model via factory)...")
    try:
        response = get_llm_client().generate(messages)
        elapsed = time.perf_counter() - t0
        logger.info(
            "[FLOW 6/6] LLM SUCCESS: total_latency=%.2fs response_chars=%d",
            elapsed, len(response),
        )
        response = run_guardrails(response, intent, context=context)
    except GuardrailViolation as exc:
        logger.error("[FLOW 6/6] GUARDRAIL BLOCKED: %s. Retrying with safe prompt.", exc)
        safe_question = "Hãy phân tích tình hình giá vàng và thị trường hiện tại dựa trên dữ liệu thật."
        safe_messages = build_answer_messages(safe_question, context, intent=intent, history=new_history, budget_chars=budget_chars)
        try:
            response = get_llm_client().generate(safe_messages)
            response = run_guardrails(response, intent, context=context)
            response += (
                "\n\n🚨 **LƯU Ý**: Hệ thống phát hiện thông tin bạn cung cấp có chứa yêu cầu "
                "bỏ qua dữ liệu hệ thống hoặc cung cấp số liệu không xác thực. Vui lòng không cung cấp "
                "thông tin giả mạo (fake news). Phân tích trên được thực hiện hoàn toàn dựa trên "
                "dữ liệu thật của thị trường."
            )
        except Exception as exc2:
            logger.error("[FLOW 6/6] SAFE RETRY FAILED: %s", exc2)
            response = _fallback_answer(intent, context, exc2)
    except Exception as exc:
        logger.error("[FLOW 6/6] LLM FAILED: %s — using fallback", exc, exc_info=True)
        response = _fallback_answer(intent, context, exc)

    return {"response": response, "intent": intent, "sources": context}


def _fallback_answer(intent: str, context: Dict[str, Any], exc: Exception) -> str:
    """Build readable answer when LLM is unavailable."""
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
