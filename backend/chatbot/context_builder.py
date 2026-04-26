"""Build grounded context for chatbot answers."""
from __future__ import annotations

from typing import Any, Dict

from tools.news_tool import get_news_summary, search_news
from tools.price_tool import get_latest_price, get_price_analysis


def build_context(question: str, intent: str) -> Dict[str, Any]:
    context: Dict[str, Any] = {"price": None, "news": None, "errors": []}

    if intent in ("price_sql", "hybrid"):
        try:
            context["price"] = get_price_analysis(type_code=_guess_type_code(question), days=7)
        except Exception as exc:
            context["errors"].append(f"price_tool: {exc}")

    if intent in ("news_rag", "hybrid"):
        try:
            context["news"] = search_news(question, top_k=5)
        except Exception as exc:
            context["errors"].append(f"news_search: {exc}")
            try:
                context["news"] = get_news_summary(days=7)
            except Exception as summary_exc:
                context["errors"].append(f"news_summary: {summary_exc}")

    return context


def _guess_type_code(question: str) -> str:
    text = question.lower()
    if "xau" in text or "thế giới" in text or "world" in text:
        return "XAUUSD"
    if "doji" in text and ("hcm" in text or "hồ chí minh" in text):
        return "DOHCML"
    if "doji" in text:
        return "DOHNL"
    if "btmc" in text:
        return "BTSJC"
    if "nhẫn" in text or "9999" in text:
        return "SJ9999"
    return "SJL1L10"
