"""Gold price query tools for the chatbot and API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from core.db import get_clickhouse_client
from ingest.price.models import TYPE_CODE_METADATA
from ingest.price.repositories.gold_price_repository import GoldPriceRepository


def get_latest_price(type_code: Optional[str] = None) -> Dict[str, Any]:
    repo = GoldPriceRepository(get_clickhouse_client())
    df = repo.get_latest_snapshot()
    if df.empty:
        return {"ok": False, "error": "Không có dữ liệu giá mới nhất."}

    if type_code:
        df = df[df["type_code"] == type_code]
        if df.empty:
            return {"ok": False, "error": f"Không có dữ liệu cho mã {type_code}."}

    records = [_format_price_row(row) for _, row in df.sort_values("type_code").iterrows()]
    return {"ok": True, "prices": records, "count": len(records)}


def get_price_analysis(type_code: str = "SJL1L10", days: int = 7) -> Dict[str, Any]:
    limit = max(days * 4, 30)
    repo = GoldPriceRepository(get_clickhouse_client())
    df = repo.get_historical_data(limit_per_type=limit)
    if df.empty:
        return {"ok": False, "error": "Không có dữ liệu lịch sử giá."}

    df = df[df["type_code"] == type_code].sort_values("ts")
    if df.empty:
        return {"ok": False, "error": f"Không có dữ liệu lịch sử cho mã {type_code}."}

    if days > 0:
        cutoff = df["ts"].max() - pd.Timedelta(days=days)
        scoped = df[df["ts"] >= cutoff]
        if not scoped.empty:
            df = scoped

    first = df.iloc[0]
    latest = df.iloc[-1]
    change = float(latest["mid_price"] - first["mid_price"])
    change_pct = (change / float(first["mid_price"]) * 100) if float(first["mid_price"]) else 0.0
    trend = "tăng" if change > 0 else "giảm" if change < 0 else "đi ngang"

    moves = df.assign(abs_change=df["price_change"].abs()).sort_values("abs_change", ascending=False).head(5)
    top_moves = [
        {
            "ts": _iso(row["ts"]),
            "mid_price": float(row["mid_price"]),
            "price_change": float(row.get("price_change", 0) or 0),
        }
        for _, row in moves.iterrows()
    ]

    rsi = float(latest.get("rsi14", 0) or 0)
    if rsi >= 70:
        rsi_summary = "quá mua"
    elif rsi <= 30 and rsi > 0:
        rsi_summary = "quá bán"
    elif rsi > 0:
        rsi_summary = "trung tính"
    else:
        rsi_summary = "chưa đủ dữ liệu"

    return {
        "ok": True,
        "type_code": type_code,
        "metadata": TYPE_CODE_METADATA.get(type_code, {}),
        "period_days": days,
        "from": _iso(first["ts"]),
        "to": _iso(latest["ts"]),
        "start_mid_price": float(first["mid_price"]),
        "latest": _format_price_row(latest),
        "change": change,
        "change_pct": round(change_pct, 4),
        "trend": trend,
        "rsi14": rsi,
        "rsi_summary": rsi_summary,
        "top_moves": top_moves,
    }


def _format_price_row(row) -> Dict[str, Any]:
    type_code = row["type_code"]
    return {
        "ts": _iso(row["ts"]),
        "type_code": type_code,
        "metadata": TYPE_CODE_METADATA.get(type_code, {}),
        "brand": row.get("brand", ""),
        "gold_type": row.get("gold_type", ""),
        "buy_price": float(row.get("buy_price", 0) or 0),
        "sell_price": float(row.get("sell_price", 0) or 0),
        "mid_price": float(row.get("mid_price", 0) or 0),
        "spread": float(row.get("spread", 0) or 0),
        "daily_return_pct": float(row.get("daily_return_pct", 0) or 0),
        "source_site": row.get("source_site", ""),
    }


def _iso(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
