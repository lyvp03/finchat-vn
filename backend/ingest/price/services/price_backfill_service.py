import time
import logging
import pandas as pd
from typing import List

from ingest.price.models import GoldPriceRecord, TYPE_CODES
from ingest.price.sources.vang_today import VangTodayCrawler
from ingest.price.parsers.vang_today_parser import VangTodayParser
from ingest.price.repositories.gold_price_repository import GoldPriceRepository
from preprocessing.compute_indicators import prepare_updates

logger = logging.getLogger("price_backfill_service")


def _records_to_dataframe(records: List[GoldPriceRecord]) -> pd.DataFrame:
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


class PriceBackfillService:
    """Điều phối luồng cào giá vàng quá khứ (Backfill)."""

    def __init__(self,
                 crawler: VangTodayCrawler,
                 parser: VangTodayParser,
                 repository: GoldPriceRepository):
        self.crawler = crawler
        self.parser = parser
        self.repository = repository

    def run_backfill(self, days: int = 30):
        """Cào dữ liệu quá khứ, tính chỉ số và lưu DB 1 lần duy nhất."""
        logger.info("=== STARTING BACKFILL (DAYS=%s) ===", days)

        # 1. Fetch + Parse
        all_records: List[GoldPriceRecord] = []
        for code in TYPE_CODES:
            payload = self.crawler.fetch_raw(code, days=days)
            records = self.parser.parse(code, payload)
            all_records.extend(records)
            time.sleep(0.3)

        if not all_records:
            logger.warning("No data fetched during backfill.")
            return

        df = _records_to_dataframe(all_records)

        # 2. Tính chỉ số kỹ thuật trực tiếp trên toàn bộ dữ liệu
        logger.info("Computing indicators for backfill data...")
        processed_df = prepare_updates(df)

        # 3. Insert toàn bộ vào DB
        self.repository.save_dataframe(processed_df)
        logger.info("=== BACKFILL COMPLETED ===")
