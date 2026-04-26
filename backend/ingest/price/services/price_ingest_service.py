import time
import logging
import pandas as pd
from typing import List

from ingest.price.models import GoldPriceRecord, TYPE_CODES
from ingest.price.sources.vang_today import VangTodayCrawler
from ingest.price.parsers.vang_today_parser import VangTodayParser
from ingest.price.repositories.gold_price_repository import GoldPriceRepository
from preprocessing.compute_indicators import prepare_updates

logger = logging.getLogger("price_ingest_service")


def _records_to_dataframe(records: List[GoldPriceRecord]) -> pd.DataFrame:
    """Chuyển danh sách GoldPriceRecord thành pandas DataFrame."""
    rows = [{
        "ts": r.ts,
        "type_code": r.type_code,
        "brand": r.brand,
        "gold_type": r.gold_type,
        "buy_price": r.buy_price,
        "sell_price": r.sell_price,
        "mid_price": r.mid_price,
        "spread": r.spread,
        "source_site": r.source_site,
    } for r in records]
    df = pd.DataFrame(rows)
    df['ts'] = pd.to_datetime(df['ts'])
    return df


class PriceIngestService:
    """Điều phối luồng cào giá vàng mới (Incremental)."""

    def __init__(self,
                 crawler: VangTodayCrawler,
                 parser: VangTodayParser,
                 repository: GoldPriceRepository):
        self.crawler = crawler
        self.parser = parser
        self.repository = repository

    def run_incremental(self):
        """Cào phiên hiện tại (1 ngày), ghép lịch sử để tính chỉ số, lưu dòng mới."""
        logger.info("=== STARTING INCREMENTAL CRAWL ===")

        # 1. Fetch + Parse
        all_records: List[GoldPriceRecord] = []
        for code in TYPE_CODES:
            payload = self.crawler.fetch_raw(code, days=1)
            records = self.parser.parse(code, payload)
            all_records.extend(records)
            time.sleep(0.3)

        if not all_records:
            logger.info("No new data fetched.")
            return

        df_new = _records_to_dataframe(all_records)

        # 2. Lấy lịch sử từ DB để làm gốc tính EMA/RSI
        df_history = self.repository.get_historical_data(limit_per_type=100)

        if not df_history.empty:
            df_combined = pd.concat([df_history, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=['ts', 'type_code'], keep='last')
        else:
            logger.warning("No historical data found. Indicators might be NaN.")
            df_combined = df_new

        # 3. Tính chỉ số kỹ thuật
        logger.info("Computing indicators for combined data...")
        processed = prepare_updates(df_combined)

        # 4. Chỉ lưu những dòng mới
        new_timestamps = df_new['ts'].unique()
        final_df = processed[processed['ts'].isin(new_timestamps)]

        self.repository.save_dataframe(final_df)
        logger.info("=== INCREMENTAL COMPLETED ===")
