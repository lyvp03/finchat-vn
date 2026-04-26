"""
News Backfill Service — điều phối luồng lấy dữ liệu quá khứ.

CLI Usage:
    python -m ingest.news.services.news_backfill_service --source kitco --limit 200
    python -m ingest.news.services.news_backfill_service --source vnexpress --limit 300
"""
import logging
from ingest.news.services.news_ingest_service import NewsIngestService
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from ingest.news.services.news_dedupe_service import NewsDedupeService

logger = logging.getLogger("news_backfill_service")


class NewsBackfillService:
    def __init__(self, ingest_service: NewsIngestService):
        self.ingest_service = ingest_service

    def run_backfill(self, limit: int = 300):
        """Chạy luồng lấy dữ liệu quá khứ (Backfill)"""
        logger.info(f"Starting backfill news ingest with limit={limit}")
        self.ingest_service.run_incremental(limit=limit)


def build_ingest_service(source: str, client) -> NewsIngestService:
    """Factory: tạo NewsIngestService với crawler/parser tương ứng nguồn."""
    repo = GoldNewsRepository(client)
    dedupe = NewsDedupeService(repo)

    if source == "vnexpress":
        from ingest.news.sources.vnexpress import VnExpressCrawler
        from ingest.news.parsers.vnexpress_parser import VnExpressParser
        return NewsIngestService(VnExpressCrawler(), VnExpressParser(), repo, dedupe)

    elif source == "kitco":
        from ingest.news.sources.kitco import KitcoCrawler
        from ingest.news.parsers.kitco_parser import KitcoParser
        return NewsIngestService(KitcoCrawler(), KitcoParser(), repo, dedupe)

    elif source == "reuters":
        # Reuters được xử lý riêng vì dùng RSS flow (không parse HTML)
        return None  # Sẽ dùng run_reuters_backfill() thay thế

    else:
        raise ValueError(f"Unknown source: {source}. Supported: vnexpress, kitco, reuters")


def run_reuters_backfill(client, limit: int = 200):
    """Backfill Reuters qua Google News RSS (flow đặc biệt, không qua HTML)."""
    from ingest.news.sources.reuters import ReutersCrawler
    from ingest.news.parsers.reuters_parser import ReutersParser

    crawler = ReutersCrawler()
    parser = ReutersParser()
    repo = GoldNewsRepository(client)
    dedupe = NewsDedupeService(repo)

    # 1. Fetch RSS
    rss_items = crawler.fetch_rss_items(limit=limit)

    # 2. Parse thành NewsArticle
    articles = []
    for item in rss_items:
        article = parser.parse_from_rss(item)
        if article:
            article.generate_hashes()
            articles.append(article)

    logger.info("Parsed %s articles from Reuters RSS.", len(articles))

    # 3. Deduplicate + Save
    new_articles = dedupe.filter_new_articles(articles)
    if new_articles:
        repo.save_bulk(new_articles)
        logger.info("Saved %s new Reuters articles.", len(new_articles))
    else:
        logger.info("No new Reuters articles to save.")


if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')

    from core.db import get_clickhouse_client

    parser = argparse.ArgumentParser(description="Gold News Backfill")
    parser.add_argument("--source", required=True, choices=["vnexpress", "kitco", "reuters"])
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    client = get_clickhouse_client()

    if args.source == "reuters":
        run_reuters_backfill(client, limit=args.limit)
    else:
        ingest = build_ingest_service(args.source, client)
        backfill = NewsBackfillService(ingest)
        backfill.run_backfill(limit=args.limit)

