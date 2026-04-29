from datetime import datetime

import pandas as pd

from tools import price_tool


def _price_df(values):
    return pd.DataFrame(
        [
            {
                "ts": ts,
                "type_code": "SJL1L10",
                "brand": "sjc",
                "gold_type": "mieng_sjc",
                "buy_price": mid - 1,
                "sell_price": mid + 1,
                "mid_price": mid,
                "spread": 2,
                "price_change": 0,
                "daily_return_pct": 0,
                "rsi14": 50,
                "source_site": "test",
            }
            for ts, mid in values
        ]
    )


class FakeRepository:
    def __init__(self, _client):
        pass

    def get_data_range(self, type_code, start, end):
        if start.month == 4:
            return _price_df(
                [
                    (datetime(2026, 4, 1), 100.0),
                    (datetime(2026, 4, 28), 110.0),
                ]
            )
        if start.month == 3:
            return _price_df(
                [
                    (datetime(2026, 3, 1), 90.0),
                    (datetime(2026, 3, 31), 96.0),
                ]
            )
        return pd.DataFrame()

    def get_historical_data(self, limit_per_type=100):
        return _price_df(
            [
                (datetime(2026, 4, 20), 100.0),
                (datetime(2026, 4, 28), 108.0),
            ]
        )


class MissingPreviousRepository(FakeRepository):
    def get_data_range(self, type_code, start, end):
        if start.month == 4:
            return _price_df([(datetime(2026, 4, 28), 110.0)])
        return pd.DataFrame()


def _patch_previous_month_range(monkeypatch):
    monkeypatch.setattr(
        price_tool,
        "extract_time_range",
        lambda question: price_tool.TimeRange(
            type="compare_previous_month",
            current_start=datetime(2026, 4, 1),
            current_end=datetime(2026, 4, 28, 10),
            previous_start=datetime(2026, 3, 1),
            previous_end=datetime(2026, 3, 31, 23, 59, 59),
        ),
    )


def test_price_tool_comparison_previous_month(monkeypatch):
    monkeypatch.setattr(price_tool, "GoldPriceRepository", FakeRepository)
    monkeypatch.setattr(price_tool, "get_clickhouse_client", lambda: object())
    _patch_previous_month_range(monkeypatch)

    result = price_tool.get_price_analysis(
        type_code="SJL1L10",
        question="Giá vàng SJC biến động gì so với tháng trước?",
    )

    assert result["ok"] is True
    assert result["type"] == "comparison"
    assert result["current_period"]["ok"] is True
    assert result["previous_period"]["ok"] is True
    assert result["comparison"]["trend"] == "cao hơn"


def test_price_tool_comparison_missing_previous_period(monkeypatch):
    monkeypatch.setattr(price_tool, "GoldPriceRepository", MissingPreviousRepository)
    monkeypatch.setattr(price_tool, "get_clickhouse_client", lambda: object())
    _patch_previous_month_range(monkeypatch)

    result = price_tool.get_price_analysis(
        type_code="SJL1L10",
        question="Giá vàng SJC biến động gì so với tháng trước?",
    )

    assert result["ok"] is False
    assert result["type"] == "comparison"
    assert result["missing"]["previous_period"] is True
