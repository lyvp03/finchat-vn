import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from ingest.news.models import NewsArticle

logger = logging.getLogger("gold_news_repository")

class GoldNewsRepository:
    def __init__(self, clickhouse_client):
        self.client = clickhouse_client
        
    def save_bulk(self, articles: List[NewsArticle]) -> bool:
        """Lưu danh sách NewsArticle vào bảng gold_news bằng 1 bulk insert"""
        if not articles:
            return True
            
        try:
            data = []
            for article in articles:
                data.append([
                    article.id,
                    article.title,
                    article.summary,
                    article.content,
                    article.source_name,
                    article.source_type,
                    article.author,
                    article.url,
                    article.canonical_url,
                    article.published_at,
                    article.crawled_at,
                    article.updated_at,
                    article.category,
                    article.language,
                    article.region,
                    article.event_type,
                    article.symbols,
                    article.tags,
                    article.entities,
                    article.sentiment_score,
                    article.impact_score,
                    article.relevance_score,
                    article.content_hash,
                    article.title_hash,
                    article.is_duplicate,
                    article.quality_score,
                    article.is_relevant,
                    article.market_scope,
                    article.raw_payload,
                    article.extra_metadata
                ])
            
            column_names = [
                'id', 'title', 'summary', 'content', 'source_name', 'source_type', 'author', 'url', 'canonical_url',
                'published_at', 'crawled_at', 'updated_at', 'category', 'language', 'region', 'event_type',
                'symbols', 'tags', 'entities', 'sentiment_score', 'impact_score', 'relevance_score',
                'content_hash', 'title_hash', 'is_duplicate', 'quality_score', 'is_relevant',
                'market_scope', 'raw_payload', 'extra_metadata'
            ]
            
            self.client.insert('gold_news', data, column_names=column_names)
            logger.info(f"Bulk inserted {len(articles)} articles to ClickHouse.")
            return True
        except Exception as e:
            logger.error(f"Failed to bulk insert articles: {e}")
            return False

    def get_existing_urls(self, urls: List[str]) -> Set[str]:
        """Trả về tập hợp các canonical_url đã tồn tại trong DB từ danh sách đầu vào"""
        if not urls:
            return set()
            
        try:
            formatted_urls = ",".join(f"'{url}'" for url in urls)
            query = f"SELECT canonical_url FROM gold_news WHERE canonical_url IN ({formatted_urls})"
            result = self.client.query(query)
            return {row[0] for row in result.result_rows}
        except Exception as e:
            logger.error(f"Error checking existing URLs: {e}")
            return set()

    def fetch_all(self, limit: int = 1000) -> List[NewsArticle]:
        """Lấy tất cả bài để enrich. Dùng FINAL để lấy row mới nhất theo ReplacingMergeTree."""
        try:
            query = f"""
                SELECT id, title, summary, content, source_name, source_type, author,
                       url, canonical_url, published_at, crawled_at, updated_at,
                       category, language, region, event_type,
                       symbols, tags, entities,
                       sentiment_score, impact_score, relevance_score,
                       content_hash, title_hash, is_duplicate, quality_score, is_relevant,
                       market_scope, raw_payload, extra_metadata
                FROM gold_news FINAL
                ORDER BY published_at DESC
                LIMIT {limit}
            """
            result = self.client.query(query)
            articles = []
            for row in result.result_rows:
                articles.append(NewsArticle(
                    id=row[0], title=row[1], summary=row[2], content=row[3],
                    source_name=row[4], source_type=row[5], author=row[6],
                    url=row[7], canonical_url=row[8],
                    published_at=row[9], crawled_at=row[10], updated_at=row[11],
                    category=row[12], language=row[13], region=row[14],
                    event_type=row[15],
                    symbols=list(row[16] or []), tags=list(row[17] or []),
                    entities=list(row[18] or []),
                    sentiment_score=float(row[19] or 0), impact_score=float(row[20] or 0),
                    relevance_score=float(row[21] or 0),
                    content_hash=row[22], title_hash=row[23],
                    is_duplicate=bool(row[24]), quality_score=float(row[25] or 1),
                    is_relevant=bool(row[26]),
                    market_scope=row[27] or "",
                    raw_payload=row[28] or "", extra_metadata=row[29] or "",
                ))
            logger.info(f"Fetched {len(articles)} articles for enrichment.")
            return articles
        except Exception as e:
            logger.error(f"Failed to fetch articles: {e}")
            return []

    def get_recent_summary(self, days: int = 7) -> Dict[str, Any]:
        """Aggregate recent relevant news for chatbot context."""
        days = max(1, int(days))
        aggregate = self.client.query(f"""
            SELECT
                count() AS total,
                avg(sentiment_score) AS avg_sentiment,
                avg(impact_score) AS avg_impact
            FROM gold_news FINAL
            WHERE published_at >= now() - INTERVAL {days} DAY
              AND is_relevant = 1
        """).first_row
        event_rows = self.client.query(f"""
            SELECT event_type, count() AS c
            FROM gold_news FINAL
            WHERE published_at >= now() - INTERVAL {days} DAY
              AND is_relevant = 1
            GROUP BY event_type
            ORDER BY c DESC
            LIMIT 5
        """).result_rows
        scope_rows = self.client.query(f"""
            SELECT market_scope, count() AS c
            FROM gold_news FINAL
            WHERE published_at >= now() - INTERVAL {days} DAY
              AND is_relevant = 1
            GROUP BY market_scope
            ORDER BY c DESC
        """).result_rows

        return {
            "days": days,
            "total": int(aggregate[0] or 0) if aggregate else 0,
            "avg_sentiment": float(aggregate[1] or 0) if aggregate else 0.0,
            "avg_impact": float(aggregate[2] or 0) if aggregate else 0.0,
            "top_event_types": [
                {"event_type": row[0] or "unknown", "count": row[1]}
                for row in event_rows
            ],
            "count_by_scope": [
                {"market_scope": row[0] or "unknown", "count": row[1]}
                for row in scope_rows
            ],
        }

    def fetch_latest_relevant(
        self,
        limit: int = 10,
        market_scope: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch latest relevant news rows for API responses."""
        limit = max(1, min(int(limit), 100))
        where = "WHERE is_relevant = 1"
        if market_scope:
            safe_scope = market_scope.replace("'", "")
            where += f" AND market_scope = '{safe_scope}'"

        rows = self.client.query(f"""
            SELECT id, title, summary, source_name, market_scope, event_type,
                   sentiment_score, impact_score, published_at
            FROM gold_news FINAL
            {where}
            ORDER BY published_at DESC
            LIMIT {limit}
        """).result_rows
        return [
            {
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "source_name": row[3],
                "market_scope": row[4],
                "event_type": row[5],
                "sentiment_score": row[6],
                "impact_score": row[7],
                "published_at": row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8]),
            }
            for row in rows
        ]

    def fetch_rag_eligible(
        self,
        limit: int = 1000,
        min_quality: float = 0.50,
        min_content_len: int = 200,
    ) -> List[Dict[str, Any]]:
        """Fetch articles eligible for RAG indexing."""
        limit = max(1, int(limit))
        min_quality = float(min_quality)
        min_content_len = max(1, int(min_content_len))

        rows = self.client.query(f"""
            SELECT id, title, summary, content, source_name, market_scope, event_type,
                   sentiment_score, impact_score, published_at
            FROM gold_news FINAL
            WHERE is_relevant = 1
              AND quality_score >= {min_quality}
              AND length(content) >= {min_content_len}
              AND is_duplicate = 0
            ORDER BY published_at DESC
            LIMIT {limit}
        """).result_rows
        return [
            {
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "content": row[3],
                "source_name": row[4],
                "market_scope": row[5],
                "event_type": row[6],
                "sentiment_score": row[7],
                "impact_score": row[8],
                "published_at": row[9],
            }
            for row in rows
        ]
