import logging
import sys
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler

# Đảm bảo import được các module (core, ingest, utils, preprocessing đều nằm trong backend/)
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# ── Price imports ──
from ingest.price.sources.vang_today import VangTodayCrawler
from ingest.price.parsers.vang_today_parser import VangTodayParser
from ingest.price.repositories.gold_price_repository import GoldPriceRepository
from ingest.price.services.price_ingest_service import PriceIngestService

# ── News imports ──
from ingest.news.sources.vnexpress import VnExpressCrawler
from ingest.news.parsers.vnexpress_parser import VnExpressParser
from ingest.news.sources.kitco import KitcoCrawler
from ingest.news.parsers.kitco_parser import KitcoParser
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from ingest.news.services.news_dedupe_service import NewsDedupeService
from ingest.news.services.news_ingest_service import NewsIngestService

from ingest.news.services.news_backfill_service import run_reuters_backfill

# ── Core imports ──
from core.db import get_clickhouse_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("worker")


def job_update_gold_price():
    logger.info("Triggering scheduled incremental gold price update...")
    try:
        client = get_clickhouse_client()
        crawler = VangTodayCrawler()
        parser = VangTodayParser()
        repository = GoldPriceRepository(client)

        service = PriceIngestService(crawler, parser, repository)
        service.run_incremental()
        logger.info("Price update completed successfully.")
    except Exception as e:
        logger.error(f"Error during price update: {e}")


def job_update_gold_news():
    logger.info("Triggering scheduled VnExpress news update...")
    try:
        client = get_clickhouse_client()
        crawler = VnExpressCrawler()
        parser = VnExpressParser()
        repository = GoldNewsRepository(client)
        dedupe_service = NewsDedupeService(repository)
        ingest_service = NewsIngestService(crawler, parser, repository, dedupe_service)

        ingest_service.run_incremental(limit=30)
        logger.info("VnExpress news update completed successfully.")
    except Exception as e:
        logger.error(f"Error during VnExpress news update: {e}")


def job_update_kitco_news():
    logger.info("Triggering scheduled Kitco news update...")
    try:
        client = get_clickhouse_client()
        crawler = KitcoCrawler()
        parser = KitcoParser()
        repository = GoldNewsRepository(client)
        dedupe_service = NewsDedupeService(repository)
        ingest_service = NewsIngestService(crawler, parser, repository, dedupe_service)

        ingest_service.run_incremental(limit=30)
        logger.info("Kitco news update completed successfully.")
    except Exception as e:
        logger.error(f"Error during Kitco news update: {e}")


def job_update_reuters_news():
    logger.info("Triggering scheduled Reuters news update...")
    try:
        client = get_clickhouse_client()
        run_reuters_backfill(client, limit=30)
        logger.info("Reuters news update completed successfully.")
    except Exception as e:
        logger.error(f"Error during Reuters news update: {e}")


def job_preprocess_news():
    logger.info("Triggering scheduled news preprocessing...")
    try:
        from preprocessing.news_enrichment import run_enrichment
        run_enrichment(limit=1000)
        logger.info("News preprocessing completed successfully.")
    except Exception as e:
        logger.error(f"Error during news preprocessing: {e}")


def job_index_news():
    logger.info("Triggering scheduled RAG news indexing...")
    try:
        from rag.indexer import run_indexing
        result = run_indexing(limit=1000)
        logger.info("RAG news indexing completed: %s", result)
    except Exception as e:
        logger.error(f"Error during RAG news indexing: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # Cào giá vàng 3 phiên/ngày
    scheduler.add_job(job_update_gold_price, 'cron', hour=9, minute=0)
    scheduler.add_job(job_update_gold_price, 'cron', hour=13, minute=0)
    scheduler.add_job(job_update_gold_price, 'cron', hour=17, minute=0)

    # Cào tin tức — mỗi nguồn lệch 10 phút để tránh chạy đồng thời
    scheduler.add_job(job_update_gold_news, 'interval', minutes=30)
    scheduler.add_job(job_update_kitco_news, 'interval', minutes=30, start_date='2026-01-01 00:10:00')
    scheduler.add_job(job_update_reuters_news, 'interval', minutes=30, start_date='2026-01-01 00:20:00')

    # Preprocessing — chạy mỗi 1 giờ, sau khi crawl xong
    scheduler.add_job(job_preprocess_news, 'interval', hours=1, start_date='2026-01-01 00:45:00')

    scheduler.add_job(job_index_news, 'interval', hours=2, start_date='2026-01-01 01:00:00')

    logger.info("Worker started. Prices at 09,13,17. News every 30m. Preprocessing every 1h. RAG indexing every 2h.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")
