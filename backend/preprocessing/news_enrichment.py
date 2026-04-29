"""
News enrichment orchestrator.
Đọc bài từ DB → chạy pipeline enrichment → ghi lại DB.

Idempotent: chạy lại nhiều lần không tạo data sai.
"""
import logging
from datetime import datetime
from typing import List

from core.config import settings
from core.db import get_clickhouse_client
from ingest.news.models import NewsArticle
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from utils.news_processing import (
    clean_text,
    compute_quality_score,
    compute_relevance_score,
    classify_market_scope,
    extract_symbols,
    extract_tags,
    extract_entities,
    classify_event_type,
    compute_impact_score,
    classify_news_tier,
)
from ml.sentiment import score_sentiment

logger = logging.getLogger("news_enrichment")


def enrich_article(article: NewsArticle) -> NewsArticle:
    """Chạy toàn bộ pipeline enrichment trên 1 bài."""
    # Phase 1: Clean text (chỉ clean 1 lần)
    article.title = clean_text(article.title)
    article.summary = clean_text(article.summary)
    article.content = clean_text(article.content)

    # Phase 2: Recompute hashes (sau clean)
    article.generate_hashes()

    # Phase 3-4: Quality + Relevance
    article.quality_score = compute_quality_score(article)
    article.relevance_score = compute_relevance_score(article)
    article.is_relevant = article.relevance_score >= settings.NEWS_RELEVANCE_THRESHOLD

    # Phase 5: Market scope
    article.market_scope = classify_market_scope(article)

    # Phase 6: Symbols → Tags → Entities (symbols truyền vào tags để tránh tính 2 lần)
    article.symbols = extract_symbols(article)
    article.tags = extract_tags(article, symbols=article.symbols)
    article.entities = extract_entities(article)

    # Phase 7: Event type (dùng tags + symbols đã có)
    article.event_type = classify_event_type(article)

    # Phase 8: Sentiment (gold-adjusted)
    text_for_sentiment = f"{article.title}. {article.summary or ''}"[:512]
    article.sentiment_score = score_sentiment(text_for_sentiment, language=article.language)

    # Phase 9: Impact (dùng event_type + relevance + quality)
    article.impact_score = compute_impact_score(article)

    # Phase 10: News tier (direct / contextual / weak)
    article.news_tier = classify_news_tier(article)

    # Mark updated
    article.updated_at = datetime.now()
    return article


def enrich_batch(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Enrich một batch bài viết."""
    enriched = []
    for i, article in enumerate(articles):
        try:
            enriched.append(enrich_article(article))
        except Exception as e:
            logger.warning(f"Failed to enrich article {article.id}: {e}")
            enriched.append(article)  # giữ nguyên bài lỗi
    return enriched


def run_enrichment(limit: int = 1000):
    """Main entry: đọc bài từ DB → enrich → bulk insert lại."""
    logger.info(f"Starting news enrichment (limit={limit})...")

    client = get_clickhouse_client()
    repo = GoldNewsRepository(client)

    articles = repo.fetch_all(limit=limit)
    if not articles:
        logger.info("No articles to enrich.")
        return

    logger.info(f"Enriching {len(articles)} articles...")
    enriched = enrich_batch(articles)

    success = repo.save_bulk(enriched)
    if success:
        logger.info(f"Enrichment complete. {len(enriched)} articles saved.")
        # Force merge để dọn row cũ ngay (ReplacingMergeTree)
        try:
            client.command("OPTIMIZE TABLE gold_news FINAL")
            logger.info("Table optimized — old rows merged.")
        except Exception as e:
            logger.warning(f"OPTIMIZE failed (non-critical): {e}")
    else:
        logger.error("Failed to save enriched articles.")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    run_enrichment(limit=limit)
