"""Market data tool for chatbot — XAUUSD, USDVND, premium calculation."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.db import get_clickhouse_client
from ingest.market.repositories.market_price_repository import MarketPriceRepository

logger = logging.getLogger("market_tool")

# 1 lượng vàng SJC = 1.20556 troy ounces
LUONG_TO_TROY_OZ = 1.20556


def get_market_analysis(symbol: str, days: int = 7) -> Dict[str, Any]:
    """
    Query market_price and return analysis similar to price_tool.

    Returns:
        {ok, symbol, from, to, period_days, trend, change, change_pct,
         latest, data_points}
    """
    client = get_clickhouse_client()
    repo = MarketPriceRepository(client)
    rows = repo.get_latest(symbol, days=days)

    if not rows:
        logger.warning("No market data for %s (last %d days)", symbol, days)
        return {"ok": False, "symbol": symbol, "error": f"No data for {symbol}"}

    first = rows[0]
    last = rows[-1]
    change = last["price"] - first["price"]
    change_pct = (change / first["price"]) * 100 if first["price"] else 0
    trend = "tăng" if change > 0 else ("giảm" if change < 0 else "đi ngang")

    # High/low in period
    prices = [r["price"] for r in rows]
    period_high = max(prices)
    period_low = min(prices)

    return {
        "ok": True,
        "symbol": symbol,
        "from": str(first["ts"])[:10],
        "to": str(last["ts"])[:10],
        "period_days": days,
        "data_points": len(rows),
        "trend": trend,
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "latest": {
            "price": last["price"],
            "ts": str(last["ts"]),
            "high": last.get("high"),
            "low": last.get("low"),
        },
        "period_high": period_high,
        "period_low": period_low,
    }


def compute_premium(
    sjc_mid: float,
    xauusd: Optional[float] = None,
    usdvnd: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute SJC premium over world gold price.

    Formula:
        world_vnd_per_luong = XAUUSD (USD/oz) * LUONG_TO_TROY_OZ * USDVND
        premium = SJC_mid - world_vnd_per_luong
    """
    if xauusd is None or usdvnd is None:
        # Fetch latest from DB
        client = get_clickhouse_client()
        repo = MarketPriceRepository(client)
        if xauusd is None:
            xau_row = repo.get_latest_price("XAUUSD")
            xauusd = xau_row["price"] if xau_row else None
        if usdvnd is None:
            vnd_row = repo.get_latest_price("USDVND")
            usdvnd = vnd_row["price"] if vnd_row else None

    if not xauusd or not usdvnd:
        missing = []
        if not xauusd:
            missing.append("XAUUSD")
        if not usdvnd:
            missing.append("USDVND")
        logger.warning("Cannot compute premium, missing: %s", missing)
        return {"ok": False, "error": f"Missing data: {', '.join(missing)}"}

    world_vnd = xauusd * LUONG_TO_TROY_OZ * usdvnd
    premium = sjc_mid - world_vnd
    premium_pct = (premium / world_vnd) * 100

    logger.info(
        "Premium: SJC_mid=%s world_vnd=%s premium=%s (%.2f%%)",
        f"{sjc_mid:,.0f}", f"{world_vnd:,.0f}", f"{premium:,.0f}", premium_pct,
    )

    return {
        "ok": True,
        "sjc_mid_price": sjc_mid,
        "xauusd": xauusd,
        "usdvnd": usdvnd,
        "world_gold_vnd_per_luong": round(world_vnd),
        "premium": round(premium),
        "premium_pct": round(premium_pct, 2),
    }
