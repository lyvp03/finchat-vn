"""Index enriched ClickHouse gold news into the configured vector store."""
from __future__ import annotations

import logging

from core.config import settings
from core.db import get_clickhouse_client
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from rag.chunker import chunk_article
from rag.store_factory import get_news_vector_store

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
        return {
            "vector_store": settings.VECTOR_STORE,
            "articles_available": 0,
            "articles_indexed": 0,
            "articles_skipped": 0,
            "chunks_created": 0,
            "chunks_indexed": 0,
            "collection_count": 0,
        }

    chunks = []
    articles_indexed = 0
    for article in articles:
        article_chunks = chunk_article(article)
        if article_chunks:
            articles_indexed += 1
            chunks.extend(article_chunks)

    store = get_news_vector_store()
    indexed = store.upsert_chunks(chunks)
    count = store.count()
    logger.info(
        "Indexed %s chunks from %s articles into %s. Collection count=%s",
        indexed,
        articles_indexed,
        settings.VECTOR_STORE,
        count,
    )
    return {
        "vector_store": settings.VECTOR_STORE,
        "articles_available": len(articles),
        "articles_indexed": articles_indexed,
        "articles_skipped": len(articles) - articles_indexed,
        "chunks_created": len(chunks),
        "chunks_indexed": indexed,
        "collection_count": count,
    }
