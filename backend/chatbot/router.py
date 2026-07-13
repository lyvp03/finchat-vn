"""Rule-based intent router for gold finance questions."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from chatbot.query_preprocessor import expand_synonyms
from chatbot.time_range import normalize_text

logger = logging.getLogger("router")


GOLD_SYMBOL_KEYWORDS = (
    "sjc",
    "sjl1l10",
    "sj9999",
    "dohnl",
    "dohcml",
    "btsjc",
    "xauusd",
    "doji",
    "btmc",
    "bao tin minh chau",
    "vang mieng",
    "vang nhan",
)

PRICE_ACTION_KEYWORDS = (
    "gia",
    "bao nhieu",
    "mua vao",
    "ban ra",
    "mid",
    "mid_price",
    "spread",
    "chenh lech",
    "tang",
    "giam",
    "bien dong",
    "xu huong",
    "cao nhat",
    "thap nhat",
    "so sanh",
)

TECHNICAL_KEYWORDS = (
    "rsi",
    "rsi14",
    "ema",
    "ema20",
    "ema50",
    "macd",
    "bollinger",
    "daily_return",
    "daily_return_pct",
    "indicator",
    "chi bao",
)

NEWS_KEYWORDS = (
    "tin",
    "tin tuc",
    "bai viet",
    "nguon tin",
    "reuters",
    "kitco",
    "vnexpress",
    "su kien",
    "event",
    "sentiment",
    "impact",
    "impact_score",
    "sentiment_score",
)

CAUSE_KEYWORDS = (
    "vi sao",
    "tai sao",
    "do dau",
    "nguyen nhan",
    "ly do",
    "anh huong",
    "tac dong",
    "lien quan",
    "giai thich",
    "co phai do",
)

MACRO_KEYWORDS = (
    "fed",
    "lai suat",
    "cpi",
    "lam phat",
    "usd",
    "dxy",
    "do la",
    "trai phieu",
    "bond yield",
    "dia chinh tri",
    "chien tranh",
    "ngan hang trung uong",
    "central bank",
)

OUT_OF_SCOPE_KEYWORDS = (
    "bitcoin",
    "btc",
    "ethereum",
    "eth",
    "crypto",
    "coin",
    "co phieu",
    "chung khoan",
    "vnindex",
    "bat dong san",
)

DEFINITION_KEYWORDS = ("la gi", "nghia la gi", "dinh nghia")
GENERIC_GOLD_KEYWORDS = ("vang",)


@dataclass(frozen=True)
class RouteResult:
    intent: str
    confidence: float
    reason: str
    signals: dict[str, Any]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text))


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    tokens = _tokens(text)
    for keyword in keywords:
        normalized = normalize_text(keyword)
        if " " in normalized:
            if normalized in text:
                return True
        elif normalized in tokens:
            return True
    return False


def analyze_question(question: str) -> RouteResult:
    text = expand_synonyms(normalize_text(question))

    has_out_of_scope = contains_any(text, OUT_OF_SCOPE_KEYWORDS)
    if has_out_of_scope:
        return RouteResult(
            intent="general",
            confidence=0.95,
            reason="Question contains out-of-scope finance keywords.",
            signals={"has_out_of_scope": True},
        )

    has_symbol = contains_any(text, GOLD_SYMBOL_KEYWORDS)
    has_generic_gold = contains_any(text, GENERIC_GOLD_KEYWORDS)
    has_price_action = contains_any(text, PRICE_ACTION_KEYWORDS)
    has_technical = contains_any(text, TECHNICAL_KEYWORDS)
    has_news = contains_any(text, NEWS_KEYWORDS)
    has_cause = contains_any(text, CAUSE_KEYWORDS)
    has_macro = contains_any(text, MACRO_KEYWORDS)
    asks_definition = contains_any(text, DEFINITION_KEYWORDS)

    signals = {
        "has_symbol": has_symbol,
        "has_generic_gold": has_generic_gold,
        "has_price_action": has_price_action,
        "has_technical": has_technical,
        "has_news": has_news,
        "has_cause": has_cause,
        "has_macro": has_macro,
        "asks_definition": asks_definition,
    }

    if asks_definition and has_technical and not (has_symbol or has_price_action):
        return RouteResult(
            intent="general",
            confidence=0.85,
            reason="Question asks for a generic technical concept definition.",
            signals=signals,
        )

    has_price_signal = has_symbol or has_price_action or has_technical
    has_cause_or_news_signal = has_news or has_cause or has_macro
    signals.update(
        {
            "has_price_signal": has_price_signal,
            "has_cause_or_news_signal": has_cause_or_news_signal,
        }
    )

    if has_price_signal and has_cause_or_news_signal:
        return RouteResult(
            intent="hybrid",
            confidence=0.9,
            reason="Question combines price signal with news/cause/macro signal.",
            signals=signals,
        )

    if has_price_signal:
        return RouteResult(
            intent="price_sql",
            confidence=0.9,
            reason="Question asks about price, movement, symbol, or technical indicator only.",
            signals=signals,
        )

    if has_cause_or_news_signal:
        return RouteResult(
            intent="news_rag",
            confidence=0.85,
            reason="Question asks about news, causes, or macro events without an explicit price data request.",
            signals=signals,
        )

    # Fallback: user mentions gold but no specific signal → treat as hybrid
    if has_generic_gold:
        return RouteResult(
            intent="hybrid",
            confidence=0.65,
            reason="Question mentions gold but no specific price/news signal. Defaulting to hybrid.",
            signals=signals,
        )

    return RouteResult(
        intent="general",
        confidence=0.6,
        reason="No clear price or news signal found.",
        signals=signals,
    )


def route_question(question: str) -> str:
    return analyze_question(question).intent


# ---------------------------------------------------------------
# History-aware routing + confidence escalation
# ---------------------------------------------------------------

CONFIDENCE_ESCALATION_THRESHOLD = 0.7


def analyze_question_with_history(
    question: str,
    history: list[dict] | None = None,
) -> RouteResult:
    """
    Intent routing có context từ lịch sử hội thoại.

    1. Chạy analyze_question bình thường.
    2. Nếu confidence < 0.8 và có history → ghép câu hỏi trước để bổ sung signal.
    3. Nếu confidence vẫn < 0.7 → escalate sang hybrid (trừ general).
    """
    route = analyze_question(question)

    # Đã rõ ràng → trả ngay
    if route.confidence >= 0.8:
        return route

    # Thử ghép history để bổ sung signal
    if history:
        last_user = next(
            (m["content"] for m in reversed(history) if m.get("role") == "user"),
            "",
        )
        if last_user:
            combined = last_user + " " + question
            route_combined = analyze_question(combined)
            if route_combined.confidence > route.confidence:
                logger.info(
                    "[INTENT] History boost: %s→%s (%.2f→%.2f)",
                    route.intent, route_combined.intent,
                    route.confidence, route_combined.confidence,
                )
                route = route_combined

    # Confidence escalation: vẫn thấp → fallback hybrid
    if route.confidence < CONFIDENCE_ESCALATION_THRESHOLD and route.intent != "general":
        logger.info(
            "[INTENT] Low confidence %.2f → escalate %s to hybrid",
            route.confidence, route.intent,
        )
        return RouteResult(
            intent="hybrid",
            confidence=route.confidence,
            reason=f"Escalated from {route.intent} due to low confidence ({route.confidence:.2f})",
            signals=route.signals,
        )

    return route
