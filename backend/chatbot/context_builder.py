"""Build grounded context for chatbot answers."""
from __future__ import annotations

import logging
from typing import Any, Dict

from chatbot.time_range import extract_time_range, normalize_text
from tools.news_tool import get_news_summary, search_news
from tools.price_tool import get_latest_price, get_price_analysis

logger = logging.getLogger("context_builder")


def build_context(question: str, intent: str) -> Dict[str, Any]:
    """
    Gọi tools phù hợp với intent và trả về context dict.

    Keys trong context:
      - price: dict từ price_tool (hoặc None)
      - news: dict từ news_tool với danh sách articles (hoặc None)
      - errors: list lỗi gặp phải trong quá trình gọi tools
      - time_range: TimeRange đã extract được
    """
    time_range = extract_time_range(question)
    context: Dict[str, Any] = {
        "price": None,
        "market": None,
        "premium": None,
        "news": None,
        "errors": [],
        "time_range": {
            "type": time_range.type,
            "period_days": time_range.period_days,
            "from": time_range.start.isoformat() if time_range.start else None,
            "to": time_range.end.isoformat() if time_range.end else None,
        },
    }

    logger.info(
        "Building context: intent=%s time_range_type=%s period_days=%s",
        intent, time_range.type, time_range.period_days,
    )

    if intent in ("price_sql", "hybrid"):
        type_code = _guess_type_code(question)
        logger.info("Fetching price: type_code=%s", type_code)
        try:
            context["price"] = get_price_analysis(
                type_code=type_code,
                days=time_range.period_days or 7,
                question=question,
            )
            logger.info(
                "Price fetched: ok=%s trend=%s change_pct=%s",
                context["price"].get("ok"),
                context["price"].get("trend"),
                context["price"].get("change_pct"),
            )
        except Exception as exc:
            logger.error("price_tool error: %s", exc, exc_info=True)
            context["errors"].append(f"price_tool: {exc}")

    # --- Market data (XAUUSD + USDVND + premium) cho hybrid ---
    if intent == "hybrid":
        try:
            from tools.market_tool import get_market_analysis, compute_premium
            days = time_range.period_days or 7

            xauusd = get_market_analysis("XAUUSD", days=days)
            usdvnd = get_market_analysis("USDVND", days=days)
            context["market"] = {"xauusd": xauusd, "usdvnd": usdvnd}
            logger.info(
                "Market data: XAUUSD ok=%s USDVND ok=%s",
                xauusd.get("ok"), usdvnd.get("ok"),
            )

            # Compute premium nếu có đủ data
            price_data = context.get("price")
            sjc_mid = (price_data or {}).get("latest", {}).get("mid_price")
            xau_price = xauusd.get("latest", {}).get("price") if xauusd.get("ok") else None
            vnd_price = usdvnd.get("latest", {}).get("price") if usdvnd.get("ok") else None

            if sjc_mid and xau_price and vnd_price:
                context["premium"] = compute_premium(sjc_mid, xau_price, vnd_price)
                logger.info(
                    "Premium computed: %s VND (%.2f%%)",
                    context["premium"].get("premium"),
                    context["premium"].get("premium_pct", 0),
                )
            else:
                logger.info("Premium skipped: sjc=%s xau=%s vnd=%s", sjc_mid, xau_price, vnd_price)

        except Exception as exc:
            logger.error("market_tool error: %s", exc, exc_info=True)
            context["errors"].append(f"market_tool: {exc}")

    if intent in ("news_rag", "hybrid"):
        # Chuyển TimeRange → unix timestamp để filter Qdrant
        from_ts = int(time_range.start.timestamp()) if time_range.start else None
        to_ts = int(time_range.end.timestamp()) if time_range.end else None
        market_scope = _guess_market_scope(question)

        logger.info(
            "Searching news: from_ts=%s to_ts=%s market_scope=%s",
            from_ts, to_ts, market_scope,
        )

        try:
            # Retrieve nhiều (RAG_CANDIDATE_K), compressor sẽ lọc top_n
            from core.config import settings
            news_result = search_news(
                query=question,
                top_k=settings.RAG_CANDIDATE_K,
                published_from_ts=from_ts,
                published_to_ts=to_ts,
                market_scope=market_scope,
            )
            found = news_result.get("count", 0)
            logger.info("News search returned %d articles (with time filter)", found)

            # Fallback: nếu không có bài nào trong window → mở rộng, đánh note
            if found == 0 and (from_ts or to_ts):
                logger.warning(
                    "No news in time window [%s, %s]. Retrying without time filter.",
                    from_ts, to_ts,
                )
                news_result = search_news(
                    query=question,
                    top_k=settings.RAG_CANDIDATE_K,
                    market_scope=market_scope,
                )
                news_result["time_filter_note"] = (
                    "Không tìm thấy tin trong giai đoạn yêu cầu. "
                    "Các tin dưới đây từ thời điểm khác trong dữ liệu."
                )
                logger.info(
                    "Fallback news search (no time filter) returned %d articles",
                    news_result.get("count", 0),
                )

            context["news"] = news_result

        except Exception as exc:
            logger.error("news_search error: %s", exc, exc_info=True)
            context["errors"].append(f"news_search: {exc}")
            # Fallback sang summary từ ClickHouse
            try:
                context["news"] = get_news_summary(days=time_range.period_days or 7)
                logger.info("Used news_summary as fallback")
            except Exception as summary_exc:
                logger.error("news_summary fallback also failed: %s", summary_exc)
                context["errors"].append(f"news_summary: {summary_exc}")

    logger.info(
        "Context ready: has_price=%s has_market=%s has_premium=%s has_news=%s errors=%d",
        context["price"] is not None,
        context["market"] is not None,
        context["premium"] is not None,
        context["news"] is not None,
        len(context["errors"]),
    )
    return context


def _guess_type_code(question: str) -> str:
    text = normalize_text(question)
    if "xau" in text or "the gioi" in text or "world" in text:
        return "XAUUSD"
    if "doji" in text and ("hcm" in text or "ho chi minh" in text):
        return "DOHCML"
    if "doji" in text:
        return "DOHNL"
    if "btmc" in text or "bao tin minh chau" in text:
        return "BTSJC"
    if "nhan" in text or "9999" in text:
        return "SJ9999"
    return "SJL1L10"


def _guess_market_scope(question: str) -> str | None:
    text = normalize_text(question)
    # World scope keywords
    if any(k in text for k in ("the gioi", "world", "xau", "usd", "fed", "dollar")):
        return "international"
    # Domestic explicit
    if any(k in text for k in ("trong nuoc", "sjc", "doji", "btmc", "noi dia")):
        return "domestic"
    # Default: không filter scope → trả cả hai
    return None
