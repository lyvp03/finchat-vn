"""Crawl XAUUSD and USDVND from Yahoo Finance using yfinance."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import yfinance as yf

logger = logging.getLogger("market.yahoo_crawler")

# Yahoo Finance ticker mapping
SYMBOL_MAP = {
    "XAUUSD": "GC=F",      # Gold Futures (USD/oz)
    "USDVND": "VND=X",     # USD/VND exchange rate
}


def fetch_market_data(
    symbol: str,
    period: str = "30d",
    interval: str = "1d",
) -> List[Dict[str, Any]]:
    """
    Fetch daily market data from Yahoo Finance.

    Args:
        symbol: Our symbol name (XAUUSD, USDVND).
        period: yfinance period string (7d, 30d, 90d, 1y, 5y, max).
        interval: yfinance interval (1d, 1h, 5m).

    Returns:
        List of dicts ready for ClickHouse insert.
    """
    ticker = SYMBOL_MAP.get(symbol)
    if not ticker:
        raise ValueError(f"Unknown symbol '{symbol}'. Available: {list(SYMBOL_MAP.keys())}")

    logger.info("Fetching %s (ticker=%s) period=%s interval=%s", symbol, ticker, period, interval)

    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
    except Exception as exc:
        logger.error("yfinance download failed for %s: %s", symbol, exc)
        raise

    if df.empty:
        logger.warning("No data returned for %s (period=%s)", symbol, period)
        return []

    # yfinance có thể trả MultiIndex columns khi download 1 ticker
    if hasattr(df.columns, "levels") and len(df.columns.levels) > 1:
        df.columns = df.columns.droplevel(1)

    rows: List[Dict[str, Any]] = []
    for ts, row in df.iterrows():
        # Ensure ts is a proper datetime
        if hasattr(ts, "to_pydatetime"):
            ts_dt = ts.to_pydatetime()
        else:
            ts_dt = datetime.fromisoformat(str(ts))

        # Strip timezone for ClickHouse DateTime
        if ts_dt.tzinfo is not None:
            ts_dt = ts_dt.replace(tzinfo=None)

        close_price = float(row.get("Close", 0) or 0)
        if close_price <= 0:
            continue

        rows.append({
            "ts": ts_dt,
            "symbol": symbol,
            "price": close_price,
            "open": float(row.get("Open", 0) or 0) or None,
            "high": float(row.get("High", 0) or 0) or None,
            "low": float(row.get("Low", 0) or 0) or None,
            "close": close_price,
            "volume": float(row.get("Volume", 0) or 0) or None,
            "source_site": "yahoo_finance",
            "interval": "daily" if interval == "1d" else interval,
        })

    logger.info("Fetched %d rows for %s", len(rows), symbol)
    return rows
