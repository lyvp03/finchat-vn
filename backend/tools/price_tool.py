"""Gold price query tools for the chatbot and API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from chatbot.time_range import TimeRange, extract_time_range
from ingest.price.models import TYPE_CODE_METADATA
from ingest.price.repositories.gold_price_repository import GoldPriceRepository


def get_clickhouse_client():
    from core.db import get_clickhouse_client as build_client

    return build_client()


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


def get_price_analysis(
    type_code: str = "SJL1L10",
    days: int = 7,
    question: str | None = None,
) -> Dict[str, Any]:
    repo = GoldPriceRepository(get_clickhouse_client())
    time_range = extract_time_range(question) if question else _rolling_time_range(days)

    if time_range.type.startswith("compare_"):
        return _get_price_comparison(repo, type_code, time_range)

    return _get_rolling_price_analysis(repo, type_code, time_range, days=days)


def _rolling_time_range(days: int) -> TimeRange:
    return TimeRange(type="rolling_period", period_days=max(1, int(days)))


def _get_rolling_price_analysis(
    repo: GoldPriceRepository,
    type_code: str,
    time_range: TimeRange,
    days: int,
) -> Dict[str, Any]:
    period_days = int(time_range.period_days or days or 7)
    limit = max(period_days * 4, 30)
    df = repo.get_historical_data(limit_per_type=limit)
    if df.empty:
        return {"ok": False, "type": "rolling", "error": "Không có dữ liệu lịch sử giá."}

    df = df[df["type_code"] == type_code].sort_values("ts")
    if df.empty:
        return {"ok": False, "type": "rolling", "error": f"Không có dữ liệu lịch sử cho mã {type_code}."}

    cutoff = df["ts"].max() - pd.Timedelta(days=period_days)
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
        "type": "rolling",
        "time_range_type": time_range.type,
        "type_code": type_code,
        "metadata": TYPE_CODE_METADATA.get(type_code, {}),
        "period_days": period_days,
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


def _get_price_comparison(
    repo: GoldPriceRepository,
    type_code: str,
    time_range: TimeRange,
) -> Dict[str, Any]:
    current_df = repo.get_data_range(type_code, time_range.current_start, time_range.current_end)
    previous_df = repo.get_data_range(type_code, time_range.previous_start, time_range.previous_end)

    current = _summarize_price_period(current_df)
    previous = _summarize_price_period(previous_df)
    result = {
        "ok": False,
        "type": "comparison",
        "time_range_type": time_range.type,
        "type_code": type_code,
        "metadata": TYPE_CODE_METADATA.get(type_code, {}),
        "requested_range": {
            "current_start": _iso(time_range.current_start),
            "current_end": _iso(time_range.current_end),
            "previous_start": _iso(time_range.previous_start),
            "previous_end": _iso(time_range.previous_end),
        },
        "current_period": current,
        "previous_period": previous,
        "missing": {
            "current_period": not current["ok"],
            "previous_period": not previous["ok"],
        },
    }

    if not current["ok"] or not previous["ok"]:
        result["error"] = "Không đủ dữ liệu để so sánh hai kỳ."
        return result

    latest_vs_previous_avg = current["latest_mid_price"] - previous["avg_mid_price"]
    current_avg_vs_previous_avg = current["avg_mid_price"] - previous["avg_mid_price"]
    if current_avg_vs_previous_avg > 0:
        trend = "cao hơn"
    elif current_avg_vs_previous_avg < 0:
        trend = "thấp hơn"
    else:
        trend = "đi ngang"

    result.update(
        {
            "ok": True,
            "comparison": {
                "latest_vs_previous_avg": latest_vs_previous_avg,
                "current_avg_vs_previous_avg": current_avg_vs_previous_avg,
                "current_avg_vs_previous_avg_pct": (
                    round(current_avg_vs_previous_avg / previous["avg_mid_price"] * 100, 4)
                    if previous["avg_mid_price"]
                    else None
                ),
                "trend": trend,
            },
        }
    )
    return result


def _summarize_price_period(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"ok": False, "reason": "No price data in this period."}

    df = df.sort_values("ts")
    first = df.iloc[0]
    latest = df.iloc[-1]
    start_mid = float(first["mid_price"])
    latest_mid = float(latest["mid_price"])
    change = latest_mid - start_mid
    change_pct = change / start_mid * 100 if start_mid else None

    return {
        "ok": True,
        "from": _iso(first["ts"]),
        "to": _iso(latest["ts"]),
        "start_mid_price": start_mid,
        "latest_mid_price": latest_mid,
        "change": change,
        "change_pct": round(change_pct, 4) if change_pct is not None else None,
        "min_mid_price": float(df["mid_price"].min()),
        "max_mid_price": float(df["mid_price"].max()),
        "avg_mid_price": float(df["mid_price"].mean()),
        "records": int(len(df)),
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
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
