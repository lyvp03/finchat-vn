import os
import time
import logging
import requests
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
import clickhouse_connect
from dotenv import load_dotenv
import sys

# Ensure backend_dir is in sys.path to import preprocessing
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from preprocessing import compute_indicators

load_dotenv(backend_dir / ".env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gold_price_ingest")

API_BASE = "https://www.vang.today/api/prices"
TYPE_CODES = ["SJL1L10", "SJ9999", "DOHNL", "DOHCML", "BTSJC", "XAUUSD"]

CLICKHOUSE_HOST = os.environ["CLICKHOUSE_HOST"]
CLICKHOUSE_PORT = int(os.environ["CLICKHOUSE_PORT"])
CLICKHOUSE_USER = os.environ["CLICKHOUSE_USER"]
CLICKHOUSE_PASSWORD = os.environ["CLICKHOUSE_PASSWORD"]
CLICKHOUSE_DATABASE = os.environ["CLICKHOUSE_DATABASE"]

TYPE_MAPPING = {
    "SJL1L10": ("sjc", "mieng_sjc"),
    "SJ9999": ("sjc", "nhan_sjc"),
    "DOHNL": ("doji", "doji_hn"),
    "DOHCML": ("doji", "doji_hcm"),
    "BTSJC": ("btmc", "btmc_sjc"),
    "XAUUSD": ("world", "xauusd"),
}

def _is_price_record(item):
    return isinstance(item, dict) and {"buy", "sell", "update_time"}.issubset(item.keys())

def _extract_records(payload):
    if isinstance(payload, list):
        return [item for item in payload if _is_price_record(item)]

    history = payload.get("history")
    if isinstance(history, list):
        normalized_records = []
        for entry in history:
            if not isinstance(entry, dict):
                continue

            date_str = entry.get("date")
            prices = entry.get("prices")
            if not date_str or not isinstance(prices, dict):
                continue

            for code, price_info in prices.items():
                if not isinstance(price_info, dict) or "buy" not in price_info or "sell" not in price_info:
                    continue

                normalized_records.append({
                    "type_code": code,
                    "buy": price_info["buy"],
                    "sell": price_info["sell"],
                    "update_time": int(datetime.strptime(date_str, "%Y-%m-%d").timestamp()),
                })
        return normalized_records

    # Fallback for other formats
    for key in ("prices", "items", "history", "rows", "result", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if _is_price_record(item)]

    return []

def get_client():
    logger.info("Connecting to ClickHouse...")
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE,
    )

def fetch_prices(type_code: str, days: int):
    logger.info("Fetching prices for type=%s days=%s", type_code, days)
    r = requests.get(API_BASE, params={"type": type_code, "days": days}, timeout=30)
    r.raise_for_status()
    payload = r.json()
    
    if not payload.get("success"):
        logger.warning("API returned success=false for type=%s", type_code)
        return []
        
    records = _extract_records(payload)
    # Filter for exact code
    records = [r for r in records if r.get("type_code") == type_code]
    
    if not records:
        logger.warning("No price records found for type=%s", type_code)
    else:
        logger.info("Fetched %s rows for type=%s", len(records), type_code)
    return records

def transform(type_code: str, item: dict):
    brand, gold_type = TYPE_MAPPING.get(type_code, ("unknown", "unknown"))
    ts = datetime.fromtimestamp(int(item["update_time"])).strftime('%Y-%m-%d %H:%M:%S')

    raw_buy = float(item.get("buy", 0) or 0)
    raw_sell = float(item.get("sell", 0) or 0)

    if type_code == "XAUUSD":
        price = raw_buy if raw_buy > 0 else raw_sell
        buy_price = price
        sell_price = price
        mid_price = price
        spread = 0.0
    else:
        buy_price = raw_buy
        sell_price = raw_sell
        mid_price = (buy_price + sell_price) / 2.0
        spread = sell_price - buy_price

    return {
        "ts": ts,
        "type_code": type_code,
        "brand": brand,
        "gold_type": gold_type,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "mid_price": mid_price,
        "spread": spread,
        "source_site": "vang.today"
    }

def none_if_nan(value):
    if pd.isna(value):
        return None
    return float(value)

def insert_df_to_db(client, df):
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
            none_if_nan(getattr(row, 'ema20', None)),
            none_if_nan(getattr(row, 'ema50', None)),
            none_if_nan(getattr(row, 'rsi14', None)),
            none_if_nan(getattr(row, 'macd', None)),
            none_if_nan(getattr(row, 'macd_signal', None)),
            none_if_nan(getattr(row, 'macd_hist', None)),
            row.source_site,
            datetime.now()
        ])
        
    logger.info("Inserting %s rows into gold_price", len(insert_data))
    client.insert(
        "gold_price",
        insert_data,
        column_names=[
            "ts", "type_code", "brand", "gold_type", "buy_price", "sell_price",
            "mid_price", "spread", "ema20", "ema50", "rsi14", "macd", "macd_signal",
            "macd_hist", "source_site", "created_at"
        ]
    )

def run_backfill(client, days=30):
    """Cào dữ liệu quá khứ (days=30), tính chỉ số và lưu DB 1 lần duy nhất."""
    logger.info("=== STARTING BACKFILL (DAYS=%s) ===", days)
    all_raw_rows = []
    
    for code in TYPE_CODES:
        data = fetch_prices(code, days=days)
        rows = [transform(code, item) for item in data]
        all_raw_rows.extend(rows)
        time.sleep(0.3)
        
    if not all_raw_rows:
        logger.warning("No data fetched during backfill.")
        return

    df = pd.DataFrame(all_raw_rows)
    df['ts'] = pd.to_datetime(df['ts'])
    
    # Tính toán chỉ số trực tiếp trên Pandas
    logger.info("Computing indicators for backfill data...")
    processed_df = compute_indicators.prepare_updates(df)
    
    # Insert toàn bộ vào DB
    insert_df_to_db(client, processed_df)
    logger.info("=== BACKFILL COMPLETED ===")

def run_incremental(client):
    """Cào phiên hiện tại (days=1), ghép với lịch sử để tính chỉ số, sau đó chỉ lưu dòng mới."""
    logger.info("=== STARTING INCREMENTAL CRAWL ===")
    new_raw_rows = []
    
    for code in TYPE_CODES:
        data = fetch_prices(code, days=1)
        rows = [transform(code, item) for item in data]
        new_raw_rows.extend(rows)
        time.sleep(0.3)
        
    if not new_raw_rows:
        logger.info("No new data fetched.")
        return
        
    df_new = pd.DataFrame(new_raw_rows)
    df_new['ts'] = pd.to_datetime(df_new['ts'])
    
    # Lấy 100 dòng dữ liệu cũ gần nhất từ ClickHouse để làm gốc tính EMA/RSI
    query = """
    SELECT * FROM (
        SELECT * FROM gold_price
        ORDER BY ts DESC
        LIMIT 100 BY type_code
    ) ORDER BY type_code, ts ASC
    """
    logger.info("Fetching historical data from DB to compute indicators...")
    try:
        df_history = client.query_df(query)
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        df_history = pd.DataFrame()
    
    if not df_history.empty:
        df_history['ts'] = pd.to_datetime(df_history['ts'])
        # Gộp dữ liệu cũ và mới
        df_combined = pd.concat([df_history, df_new], ignore_index=True)
        # Bỏ trùng lặp (nếu data mới trùng data cũ thì ưu tiên data mới 'last')
        df_combined = df_combined.drop_duplicates(subset=['ts', 'type_code'], keep='last')
    else:
        logger.warning("No historical data found in DB. Indicators might be NaN.")
        df_combined = df_new
        
    # Chạy tiền xử lý trên dữ liệu gộp
    logger.info("Computing indicators for combined data...")
    processed_combined = compute_indicators.prepare_updates(df_combined)
    
    # LỌC: Chỉ lấy ra những dòng mới sinh ra trong đợt crawl này
    new_timestamps = df_new['ts'].unique()
    final_new_df = processed_combined[processed_combined['ts'].isin(new_timestamps)]
    
    # Insert vào DB
    insert_df_to_db(client, final_new_df)
    logger.info("=== INCREMENTAL COMPLETED ===")

def main():
    parser = argparse.ArgumentParser(description="Gold Price Ingestion Pipeline")
    parser.add_argument("--mode", choices=["backfill", "incremental"], default="incremental", 
                        help="Chọn 'backfill' để cào 30 ngày, 'incremental' để cào hiện tại (mặc định)")
    parser.add_argument("--days", type=int, default=30, help="Số ngày khi chạy backfill")
    
    args = parser.parse_args()
    client = get_client()
    
    try:
        if args.mode == "backfill":
            run_backfill(client, days=args.days)
        else:
            run_incremental(client)
    except Exception as e:
        logger.exception("Pipeline failed")
        raise

if __name__ == "__main__":
    main()
