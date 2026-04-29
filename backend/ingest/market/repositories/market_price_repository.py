"""ClickHouse repository for market_price table."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("market.repository")


class MarketPriceRepository:
    def __init__(self, client):
        self.client = client
        self.table = "market_price"

    def upsert_batch(self, rows: List[Dict[str, Any]]) -> int:
        """Insert rows into market_price. ReplacingMergeTree handles dedup."""
        if not rows:
            return 0

        columns = ["ts", "symbol", "price", "open", "high", "low", "close",
                    "volume", "source_site", "interval"]
        data = []
        for row in rows:
            data.append([row.get(c) for c in columns])

        self.client.insert(
            self.table,
            data,
            column_names=columns,
        )
        logger.info("Inserted %d rows into %s", len(rows), self.table)
        return len(rows)

    def get_latest(
        self,
        symbol: str,
        days: int = 30,
        interval: str = "daily",
    ) -> List[Dict[str, Any]]:
        """Fetch latest N days of data for a symbol."""
        query = """
            SELECT ts, symbol, price, open, high, low, close, volume, source_site, interval
            FROM {table}
            WHERE symbol = %(symbol)s
              AND interval = %(interval)s
              AND ts >= now() - INTERVAL %(days)s DAY
            ORDER BY ts ASC
        """.format(table=self.table)

        result = self.client.query(
            query,
            parameters={"symbol": symbol, "interval": interval, "days": days},
        )

        columns = ["ts", "symbol", "price", "open", "high", "low", "close",
                    "volume", "source_site", "interval"]
        rows = [dict(zip(columns, row)) for row in result.result_rows]
        logger.info("Fetched %d rows for %s (last %d days)", len(rows), symbol, days)
        return rows

    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch the single most recent price for a symbol."""
        query = """
            SELECT ts, symbol, price, open, high, low, close
            FROM {table}
            WHERE symbol = %(symbol)s
            ORDER BY ts DESC
            LIMIT 1
        """.format(table=self.table)

        result = self.client.query(query, parameters={"symbol": symbol})
        if not result.result_rows:
            return None

        columns = ["ts", "symbol", "price", "open", "high", "low", "close"]
        return dict(zip(columns, result.result_rows[0]))

    def count(self, symbol: str) -> int:
        """Count total rows for a symbol."""
        query = "SELECT count() FROM {table} WHERE symbol = %(symbol)s".format(table=self.table)
        result = self.client.query(query, parameters={"symbol": symbol})
        return result.result_rows[0][0] if result.result_rows else 0
