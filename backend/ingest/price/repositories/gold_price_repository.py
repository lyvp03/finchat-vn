import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger("gold_price_repository")


def _zero_if_nan(value):
    """Convert NaN/None to 0.0 for non-nullable Float64 columns."""
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


class GoldPriceRepository:
    """Read/write gold price data in ClickHouse."""

    def __init__(self, clickhouse_client):
        self.client = clickhouse_client

    def get_historical_data(self, limit_per_type: int = 100) -> pd.DataFrame:
        """Fetch the latest N rows per type_code. FINAL removes replaced rows."""
        query = f"""
        SELECT * FROM (
            SELECT * FROM gold_price FINAL
            ORDER BY ts DESC
            LIMIT {limit_per_type} BY type_code
        ) ORDER BY type_code, ts ASC
        """
        logger.info("Fetching historical data (limit=%s per type) from DB...", limit_per_type)
        try:
            df = self.client.query_df(query)
            if not df.empty:
                df["ts"] = pd.to_datetime(df["ts"])
            return df
        except Exception as e:
            logger.error("Failed to fetch history: %s", e)
            return pd.DataFrame()

    def get_latest_snapshot(self) -> pd.DataFrame:
        """Fetch the latest row for each type_code."""
        query = """
        SELECT * FROM gold_price FINAL
        ORDER BY ts DESC
        LIMIT 1 BY type_code
        """
        try:
            df = self.client.query_df(query)
            if not df.empty:
                df["ts"] = pd.to_datetime(df["ts"])
            return df
        except Exception as e:
            logger.error("Failed to fetch latest snapshot: %s", e)
            return pd.DataFrame()

    def get_data_range(self, type_code: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch one gold type in an explicit timestamp range."""
        query = """
        SELECT *
        FROM gold_price FINAL
        WHERE type_code = {type_code:String}
          AND ts >= {start:DateTime}
          AND ts <= {end:DateTime}
        ORDER BY ts ASC
        """
        try:
            df = self.client.query_df(
                query,
                parameters={"type_code": type_code, "start": start, "end": end},
            )
            if not df.empty:
                df["ts"] = pd.to_datetime(df["ts"])
            return df
        except Exception as e:
            logger.error("Failed to fetch data range for type=%s: %s", type_code, e)
            return pd.DataFrame()

    def save_dataframe(self, df: pd.DataFrame):
        """Bulk insert an indicator-ready DataFrame into gold_price."""
        if df.empty:
            logger.info("No rows to insert.")
            return

        insert_data = []
        for row in df.itertuples(index=False):
            insert_data.append([
                pd.Timestamp(row.ts).to_pydatetime(),
                row.type_code,
                row.brand,
                row.gold_type,
                float(row.buy_price),
                float(row.sell_price),
                float(row.mid_price),
                float(row.spread),
                _zero_if_nan(getattr(row, "spread_pct", 0)),
                _zero_if_nan(getattr(row, "price_change", 0)),
                _zero_if_nan(getattr(row, "daily_return_pct", 0)),
                _zero_if_nan(getattr(row, "ema20", 0)),
                _zero_if_nan(getattr(row, "ema50", 0)),
                _zero_if_nan(getattr(row, "rsi14", 0)),
                _zero_if_nan(getattr(row, "macd", 0)),
                _zero_if_nan(getattr(row, "macd_signal", 0)),
                _zero_if_nan(getattr(row, "macd_hist", 0)),
                getattr(row, "source_site", "vang.today"),
                datetime.now(),
            ])

        column_names = [
            "ts", "type_code", "brand", "gold_type", "buy_price", "sell_price",
            "mid_price", "spread", "spread_pct", "price_change", "daily_return_pct",
            "ema20", "ema50", "rsi14", "macd", "macd_signal",
            "macd_hist", "source_site", "created_at",
        ]

        logger.info("Bulk inserting %s rows into gold_price", len(insert_data))
        self.client.insert("gold_price", insert_data, column_names=column_names)

    def get_timeseries(self, type_code: str, days: int = 30) -> list[dict]:
        """Fetch timeseries data for the price chart."""
        query = """
        SELECT ts, buy_price, sell_price, mid_price
        FROM gold_price FINAL
        WHERE type_code = {type_code:String}
          AND ts >= now() - INTERVAL {days:UInt32} DAY
        ORDER BY ts ASC
        """
        try:
            df = self.client.query_df(
                query,
                parameters={"type_code": type_code, "days": int(days)},
            )
            if df.empty:
                return []
            df["ts"] = pd.to_datetime(df["ts"]).dt.strftime('%Y-%m-%dT%H:%M:%S')
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error("Failed to fetch timeseries: %s", e)
            return []
