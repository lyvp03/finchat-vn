"""Main chatbot flow."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from chatbot.context_builder import build_context
from chatbot.prompts import build_answer_messages
from chatbot.router import route_question
from core.llm.factory import get_llm_client


def answer_question(question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    intent = route_question(question)
    if intent == "general":
        return {
            "response": "Câu hỏi này nằm ngoài phạm vi dữ liệu giá vàng và tin tức vàng hiện có.",
            "intent": intent,
            "sources": {"price": None, "news": None, "errors": []},
        }

    context = build_context(question, intent)
    if context.get("errors") and not context.get("price") and not context.get("news"):
        return {
            "response": "Hiện chưa truy vấn được dữ liệu nền để trả lời chính xác. Vui lòng kiểm tra ClickHouse/ChromaDB/Ollama.",
            "intent": intent,
            "sources": context,
        }

    messages = build_answer_messages(question, context, history=history)
    try:
        response = get_llm_client().generate(messages)
    except Exception as exc:
        response = _fallback_answer(intent, context, exc)

    return {"response": response, "intent": intent, "sources": context}


def _fallback_answer(intent: str, context: Dict[str, Any], exc: Exception) -> str:
    parts = [f"Không gọi được LLM ({exc}). Dữ liệu truy vấn được:"]
    price = context.get("price")
    news = context.get("news")
    if intent in ("price_sql", "hybrid") and price:
        parts.append(str(price))
    if intent in ("news_rag", "hybrid") and news:
        parts.append(str(news))
    return "\n".join(parts)
