"""
Preprocessing Orchestrator: Đọc dữ liệu từ DB → Tính chỉ số kỹ thuật → Ghi lại DB.
"""
import logging
import pandas as pd

from utils.indicators import compute_indicators_per_group, none_if_nan
from ingest.price.repositories.gold_price_repository import GoldPriceRepository

logger = logging.getLogger("compute_indicators")


def prepare_updates(df: pd.DataFrame) -> pd.DataFrame:
    """Dedupe + tính chỉ số kỹ thuật cho toàn bộ DataFrame, nhóm theo type_code."""
    # Dedupe by ts + type_code, giữ bản ghi mới nhất
    before = len(df)
    if "created_at" in df.columns:
        df = df.sort_values(["ts", "type_code", "created_at"])
    else:
        df = df.sort_values(["ts", "type_code"])
    df = df.drop_duplicates(subset=["ts", "type_code"], keep="last")
    after = len(df)
    if before != after:
        logger.info("Deduped %s → %s rows (removed %s)", before, after, before - after)

    grouped = []
    for type_code, subdf in df.groupby("type_code", sort=False):
        logger.info("Computing indicators for type=%s rows=%s", type_code, len(subdf))
        grouped.append(compute_indicators_per_group(subdf))

    result = pd.concat(grouped, ignore_index=True)
    result = result.sort_values(["type_code", "ts"]).reset_index(drop=True)
    logger.info("Prepared %s rows with indicators", len(result))
    return result


def run_full_recompute(client):
    """
    Đọc toàn bộ giá vàng từ DB, tính lại chỉ số kỹ thuật,
    và cập nhật (ghi đè) lại vào bảng gold_price.
    """
    repo = GoldPriceRepository(client)

    # 1. Đọc toàn bộ dữ liệu từ DB (FINAL đã loại duplicate)
    logger.info("Fetching all price data from DB...")
    df = repo.get_historical_data(limit_per_type=10000)
    if df.empty:
        logger.warning("gold_price is empty, nothing to recompute.")
        return

    # 2. Tính chỉ số kỹ thuật (dedupe thêm lần nữa cho chắc)
    result = prepare_updates(df)

    # 3. Ghi lại vào DB
    repo.save_dataframe(result)

    # 4. Force merge
    try:
        client.command("OPTIMIZE TABLE gold_price FINAL")
        logger.info("Table optimized — old rows merged.")
    except Exception as e:
        logger.warning("OPTIMIZE failed (non-critical): %s", e)

    logger.info("Recomputed indicators for %s rows", len(result))

