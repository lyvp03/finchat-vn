"""Market data ingest service — incremental + backfill."""
from __future__ import annotations

import logging
from typing import List

from ingest.market.sources.yahoo_crawler import fetch_market_data, SYMBOL_MAP
from ingest.market.repositories.market_price_repository import MarketPriceRepository

logger = logging.getLogger("market.ingest_service")

# Default symbols to crawl
DEFAULT_SYMBOLS = ["XAUUSD", "USDVND"]


class MarketIngestService:
    def __init__(self, repository: MarketPriceRepository):
        self.repository = repository

    def run_incremental(self, symbols: List[str] | None = None, period: str = "7d"):
        """
        Fetch recent data. Called by worker scheduler (3×/day).
        ReplacingMergeTree handles dedup nếu data trùng.
        """
        symbols = symbols or DEFAULT_SYMBOLS
        total = 0
        for symbol in symbols:
            try:
                rows = fetch_market_data(symbol, period=period, interval="1d")
                inserted = self.repository.upsert_batch(rows)
                total += inserted
                logger.info(
                    "[INCREMENTAL] %s: fetched=%d inserted=%d",
                    symbol, len(rows), inserted,
                )
            except Exception as exc:
                logger.error("[INCREMENTAL] %s failed: %s", symbol, exc, exc_info=True)

        logger.info("[INCREMENTAL] Total inserted: %d", total)
        return total

    def run_backfill(self, symbols: List[str] | None = None, period: str = "1y"):
        """
        Backfill historical data. Run once manually.

        Periods: 30d, 90d, 6mo, 1y, 2y, 5y, max
        """
        symbols = symbols or DEFAULT_SYMBOLS
        total = 0
        for symbol in symbols:
            existing = self.repository.count(symbol)
            logger.info(
                "[BACKFILL] %s: existing rows=%d, fetching period=%s",
                symbol, existing, period,
            )
            try:
                rows = fetch_market_data(symbol, period=period, interval="1d")
                inserted = self.repository.upsert_batch(rows)
                total += inserted
                logger.info(
                    "[BACKFILL] %s: fetched=%d inserted=%d total_in_db=%d",
                    symbol, len(rows), inserted,
                    self.repository.count(symbol),
                )
            except Exception as exc:
                logger.error("[BACKFILL] %s failed: %s", symbol, exc, exc_info=True)

        logger.info("[BACKFILL] Total inserted: %d", total)
        return total


def run_backfill_cli(period: str = "1y"):
    """Standalone backfill entry point — can be called from CLI or script."""
    from core.db import get_clickhouse_client

    client = get_clickhouse_client()
    repo = MarketPriceRepository(client)
    service = MarketIngestService(repo)
    return service.run_backfill(period=period)


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )
    period = sys.argv[1] if len(sys.argv) > 1 else "1y"
    print(f"Backfilling market data with period={period}...")
    total = run_backfill_cli(period=period)
    print(f"Done. Total rows inserted: {total}")
