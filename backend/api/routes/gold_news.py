from fastapi import APIRouter, Query, HTTPException

from core.db import get_clickhouse_client
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from tools.news_tool import search_news

router = APIRouter(prefix="/api/news", tags=["gold_news"])


@router.get("/summary")
def news_summary(days: int = 7):
    """Trả về thống kê tổng hợp tin tức N ngày gần nhất."""
    repository = GoldNewsRepository(get_clickhouse_client())
    return {"ok": True, **repository.get_recent_summary(days=days)}


@router.get("/latest")
def latest_news(limit: int = 10, market_scope: str | None = None):
    repository = GoldNewsRepository(get_clickhouse_client())
    return {"ok": True, "articles": repository.fetch_latest_relevant(limit=limit, market_scope=market_scope)}


@router.get("/latest-extended")
def latest_news_extended(limit: int = 20, market_scope: str | None = None):
    """Trả về tin tức mới nhất kèm url và news_tier."""
    repository = GoldNewsRepository(get_clickhouse_client())
    return {"ok": True, "articles": repository.fetch_latest_extended(limit=limit, market_scope=market_scope)}


@router.get("/search")
def news_search(q: str = Query(...), top_k: int = 5, market_scope: str | None = None):
    return search_news(query=q, top_k=top_k, market_scope=market_scope)


@router.get("/{article_id}")
def news_detail(article_id: str):
    """Trả về chi tiết 1 bài viết theo ID."""
    repository = GoldNewsRepository(get_clickhouse_client())
    article = repository.fetch_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"ok": True, "article": article}
