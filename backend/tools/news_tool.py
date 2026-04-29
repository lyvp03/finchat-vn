"""Gold news query tools."""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.config import settings
from core.db import get_clickhouse_client
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from rag.store_factory import get_news_vector_store


def search_news(
    query: str,
    market_scope: Optional[str] = None,
    top_k: Optional[int] = None,
    event_type: Optional[str] = None,
    published_from_ts: Optional[int] = None,
    published_to_ts: Optional[int] = None,
    source_name: Optional[str] = None,
) -> Dict[str, Any]:
    top_k = top_k or settings.RAG_TOP_K
    store = get_news_vector_store()
    rows = store.search(
        query=query,
        top_k=top_k,
        market_scope=market_scope,
        event_type=event_type,
        published_from_ts=published_from_ts,
        published_to_ts=published_to_ts,
        source_name=source_name,
    )
    return {
        "ok": True,
        "query": query,
        "vector_store": settings.VECTOR_STORE,
        "articles": rows,
        "count": len(rows),
    }


def get_news_summary(days: int = 7) -> Dict[str, Any]:
    repository = GoldNewsRepository(get_clickhouse_client())
    return {"ok": True, **repository.get_recent_summary(days=days)}
