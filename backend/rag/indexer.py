"""Index enriched ClickHouse gold news into ChromaDB."""
from __future__ import annotations

import logging

from core.config import settings
from core.db import get_clickhouse_client
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from rag.vector_store import GoldNewsVectorStore

logger = logging.getLogger("rag_indexer")


def fetch_rag_eligible_articles(limit: int = 1000) -> list[dict]:
    repository = GoldNewsRepository(get_clickhouse_client())
    return repository.fetch_rag_eligible(
        limit=limit,
        min_quality=settings.NEWS_QUALITY_MIN_RAG,
        min_content_len=settings.RAG_MIN_CONTENT_LEN,
    )


def run_indexing(limit: int = 1000) -> dict:
    articles = fetch_rag_eligible_articles(limit=limit)
    if not articles:
        logger.info("No RAG-eligible articles found.")
        return {"indexed": 0, "available": 0}

    store = GoldNewsVectorStore()
    indexed = store.upsert_articles(articles)
    count = store.count()
    logger.info("Indexed %s articles into ChromaDB. Collection count=%s", indexed, count)
    return {"indexed": indexed, "available": count}
