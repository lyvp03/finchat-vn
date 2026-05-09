"""
News enrichment orchestrator.
Đọc bài từ DB → chạy pipeline enrichment → ghi lại DB.

Strategy:
  1. Quality score + symbol/tag/entity extraction → rule-based (fast, reliable)
  2. Sentiment + relevance + impact + event_type + market_scope + news_tier
     → LLM (GPT-5-mini) with detailed rubrics
     → fallback to rule-based heuristics if LLM fails

Idempotent: chạy lại nhiều lần không tạo data sai.
"""
import logging
from datetime import datetime
from typing import List

from core.config import settings
from core.db import get_clickhouse_client
from ingest.news.models import NewsArticle
from ingest.news.repositories.gold_news_repository import GoldNewsRepository

# Rule-based functions (used for quality/extraction + LLM fallback)
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

# LLM-based unified analyzer (primary for scoring/classification)
from ml.news_analyzer import analyze_article

# Removed legacy sentiment import

logger = logging.getLogger("news_enrichment")


def _apply_llm_analysis(article: NewsArticle) -> bool:
    """Try LLM analysis. Returns True if successful, False → use fallback."""
    result = analyze_article(
        title=article.title,
        content=f"{article.summary or ''} {article.content or ''}",
        source_name=article.source_name,
        language=article.language,
    )
    if result is None:
        return False

    article.sentiment_score = result.sentiment_score
    article.relevance_score = result.relevance_score
    article.impact_score = result.impact_score
    article.event_type = result.event_type
    article.market_scope = result.market_scope
    article.news_tier = result.news_tier
    return True


def _apply_rule_based_fallback(article: NewsArticle) -> None:
    """Fallback: use original rule-based heuristics for all scoring fields."""
    article.relevance_score = compute_relevance_score(article)
    article.market_scope = classify_market_scope(article)
    article.event_type = classify_event_type(article)

    # Fallback sentiment is purely 0.0 when LLM is completely down
    article.sentiment_score = 0.0

    article.impact_score = compute_impact_score(article)
    article.news_tier = classify_news_tier(article)


def enrich_article(article: NewsArticle) -> tuple[NewsArticle, bool]:
    """Chạy toàn bộ pipeline enrichment trên 1 bài."""
    # ── Phase 1: Clean text ──
    article.title = clean_text(article.title)
    article.summary = clean_text(article.summary)
    article.content = clean_text(article.content)

    # ── Phase 2: Recompute hashes ──
    article.generate_hashes()

    # ── Phase 3: Quality score (always rule-based — metadata check) ──
    article.quality_score = compute_quality_score(article)

    # ── Phase 4: Symbols → Tags → Entities (always rule-based — dict lookup) ──
    article.symbols = extract_symbols(article)
    article.tags = extract_tags(article, symbols=article.symbols)
    article.entities = extract_entities(article)

    # ── Phase 5: LLM analysis (sentiment + relevance + impact + event_type + scope + tier) ──
    llm_ok = _apply_llm_analysis(article)
    if not llm_ok:
        logger.warning("LLM unavailable for article %s — using rule-based fallback", article.id[:12])
        _apply_rule_based_fallback(article)

    # ── Phase 6: Derived fields ──
    article.is_relevant = article.relevance_score >= settings.NEWS_RELEVANCE_THRESHOLD

    # Mark updated
    article.updated_at = datetime.now()
    return article, llm_ok


import concurrent.futures

def enrich_batch(articles: List[NewsArticle], max_workers: int = 10) -> List[NewsArticle]:
    """Enrich một batch bài viết (chạy song song để tối ưu tốc độ)."""
    enriched = []
    llm_count = 0
    fallback_count = 0
    error_count = 0
    
    total = len(articles)
    
    def process(article):
        try:
            return enrich_article(article), None
        except Exception as e:
            return (article, False), e

    logger.info(f"Starting parallel enrichment with {max_workers} workers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process, article): article for article in articles}
        
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            (result_article, used_llm), error = future.result()
            
            if error:
                error_count += 1
                logger.error("Failed to enrich article %s: %s", result_article.id[:12], error)
            elif used_llm:
                llm_count += 1
            else:
                fallback_count += 1
                
            enriched.append(result_article)
            
            # Log progress every 50 articles
            if i % 50 == 0 or i == total:
                logger.info("Progress: %d/%d articles processed (LLM: %d, Fallback: %d, Errors: %d)",
                            i, total, llm_count, fallback_count, error_count)

    logger.info(
        "Batch enrichment FINISHED. Total: %d | LLM Success: %d | Fallbacks: %d | Errors: %d",
        total, llm_count, fallback_count, error_count
    )
    return enriched


def run_enrichment(limit: int = 1000):
    """Main entry: đọc bài từ DB → enrich → bulk insert lại."""
    logger.info(f"Starting news enrichment (limit={limit})...")

    client = get_clickhouse_client()
    repo = GoldNewsRepository(client)

    articles = repo.fetch_unenriched(limit=limit)
    if not articles:
        logger.info("No unenriched articles found — skipping.")
        return

    logger.info(f"Enriching {len(articles)} unenriched articles...")
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
