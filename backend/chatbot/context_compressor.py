"""Compress retrieved news articles thành evidence blocks compact cho LLM."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.config import settings

logger = logging.getLogger("context_compressor")


def compact_news_context(
    articles: List[Dict[str, Any]],
    top_n: int | None = None,
    max_chars_per_article: int | None = None,
) -> str:
    """
    Rút gọn danh sách articles thành evidence blocks để đưa vào LLM.

    Args:
        articles: Danh sách articles từ vector store search.
        top_n: Số bài tối đa đưa vào LLM (default: RAG_CONTEXT_TOP_N).
        max_chars_per_article: Ký tự tối đa mỗi bài (default: RAG_CONTEXT_MAX_CHARS).

    Returns:
        Chuỗi evidence blocks dạng text.
    """
    top_n = top_n if top_n is not None else settings.RAG_CONTEXT_TOP_N
    max_chars = max_chars_per_article if max_chars_per_article is not None else settings.RAG_CONTEXT_MAX_CHARS

    if not articles:
        logger.debug("compact_news_context: no articles to compact")
        return "(Không có tin tức nào được tìm thấy.)"

    # Sort by relevance score (vector similarity), cao nhất trước
    sorted_articles = sorted(
        articles,
        key=lambda a: float(a.get("score") or 0),
        reverse=True,
    )
    top_articles = sorted_articles[:top_n]

    logger.info(
        "Compacting news: total=%d → top_n=%d, max_chars=%d",
        len(articles), len(top_articles), max_chars,
    )

    blocks = []
    for i, article in enumerate(top_articles, start=1):
        doc = article.get("document", "") or ""
        if len(doc) > max_chars:
            # Cắt ở ranh giới từ
            short_doc = doc[:max_chars].rsplit(" ", 1)[0] + "..."
        else:
            short_doc = doc

        published = (article.get("published_at") or "")[:10]  # Chỉ lấy date
        score = article.get("score")
        score_str = f"{score:.3f}" if score is not None else "N/A"

        block = (
            f"[{i}] {article.get('title', 'N/A')}\n"
            f"Nguồn: {article.get('source_name', 'N/A')} | "
            f"Ngày: {published} | "
            f"Event: {article.get('event_type', 'N/A')} | "
            f"Impact: {article.get('impact_score', 0):.2f} | "
            f"Sentiment: {article.get('sentiment_score', 0):+.2f} | "
            f"Tier: {article.get('news_tier', 'contextual')} | "
            f"Scope: {article.get('market_scope', 'N/A')} | "
            f"Relevance: {score_str}\n"
            f"Nội dung:\n{short_doc}"
        )
        blocks.append(block)
        logger.debug(
            "  [%d] %s | %s | chars=%d",
            i, article.get("title", "")[:60], published, len(short_doc),
        )

    return "\n\n---\n\n".join(blocks)


def format_price_context(price: Dict[str, Any] | None) -> str:
    """Format price data thành text ngắn gọn cho prompt."""
    if not price or not price.get("ok"):
        reason = (price or {}).get("error", "Không có dữ liệu giá.")
        logger.debug("format_price_context: no price data — %s", reason)
        return f"(Không có dữ liệu giá: {reason})"

    price_type = price.get("type", "rolling")

    if price_type == "rolling":
        latest = price.get("latest", {})
        lines = []
        # Include fallback note if this was originally a comparison request
        comparison_note = price.get("_comparison_note")
        if comparison_note:
            lines.append(f"[NOTE] {comparison_note}")
        lines.extend([
            f"Mã vàng: {price.get('type_code')} ({price.get('metadata', {}).get('name', '')})",
            f"Giai đoạn: {price.get('from', '')[:10]} → {price.get('to', '')[:10]} ({price.get('period_days')} ngày)",
            f"Xu hướng: {price.get('trend')} | Thay đổi: {price.get('change', 0):+,.0f} ({price.get('change_pct', 0):+.2f}%)",
            f"Giá mới nhất: mua {latest.get('buy_price', 0):,.0f} / bán {latest.get('sell_price', 0):,.0f} (mid: {latest.get('mid_price', 0):,.0f})",
            f"RSI14: {price.get('rsi14', 0):.1f} → {price.get('rsi_summary', 'N/A')}",
        ])
        top_moves = price.get("top_moves", [])
        if top_moves:
            lines.append("Top biến động:")
            for move in top_moves[:3]:
                lines.append(
                    f"  - {move.get('ts', '')[:10]}: {move.get('price_change', 0):+,.0f} (mid={move.get('mid_price', 0):,.0f})"
                )
        return "\n".join(lines)

    if price_type == "comparison":
        current = price.get("current_period", {})
        previous = price.get("previous_period", {})
        comp = price.get("comparison", {})
        lines = [
            f"So sánh ({price.get('time_range_type')}): {price.get('type_code')}",
            f"Kỳ hiện tại: {current.get('from', '')[:10]} → avg {current.get('avg_mid_price', 0):,.0f}",
            f"Kỳ trước: {previous.get('from', '')[:10]} → avg {previous.get('avg_mid_price', 0):,.0f}",
        ]
        if comp:
            lines.append(
                f"Chênh lệch: {comp.get('current_avg_vs_previous_avg', 0):+,.0f} "
                f"({comp.get('current_avg_vs_previous_avg_pct', 0):+.2f}%) → {comp.get('trend', 'N/A')}"
            )
        return "\n".join(lines)

    return str(price)
