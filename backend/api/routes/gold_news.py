from fastapi import APIRouter, Query

from core.db import get_clickhouse_client
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from tools.news_tool import search_news

router = APIRouter(prefix="/api/news", tags=["gold_news"])


@router.get("/latest")
def latest_news(limit: int = 10, market_scope: str | None = None):
    repository = GoldNewsRepository(get_clickhouse_client())
    return {"ok": True, "articles": repository.fetch_latest_relevant(limit=limit, market_scope=market_scope)}


@router.get("/search")
def news_search(q: str = Query(...), top_k: int = 5, market_scope: str | None = None):
    return search_news(query=q, top_k=top_k, market_scope=market_scope)
