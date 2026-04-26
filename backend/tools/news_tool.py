"""Gold news query tools."""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.config import settings
from core.db import get_clickhouse_client
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from rag.vector_store import GoldNewsVectorStore


def search_news(
    query: str,
    market_scope: Optional[str] = None,
    top_k: Optional[int] = None,
) -> Dict[str, Any]:
    top_k = top_k or settings.RAG_TOP_K
    store = GoldNewsVectorStore()
    rows = store.search(query=query, top_k=top_k, market_scope=market_scope)
    return {"ok": True, "query": query, "articles": rows, "count": len(rows)}


def get_news_summary(days: int = 7) -> Dict[str, Any]:
    repository = GoldNewsRepository(get_clickhouse_client())
    return {"ok": True, **repository.get_recent_summary(days=days)}
