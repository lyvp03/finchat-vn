import logging
from datetime import datetime
from typing import List
from ingest.price.models import GoldPriceRecord, TYPE_MAPPING

logger = logging.getLogger("vang_today_parser")


class VangTodayParser:
    """Chuyển đổi payload JSON thô từ API thành danh sách GoldPriceRecord."""

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _is_price_record(item: dict) -> bool:
        return isinstance(item, dict) and {"buy", "sell", "update_time"}.issubset(item.keys())

    def _extract_records(self, payload: dict) -> List[dict]:
        """Trích xuất danh sách bản ghi giá thô từ nhiều định dạng API khác nhau."""
        if isinstance(payload, list):
            return [item for item in payload if self._is_price_record(item)]

        history = payload.get("history")
        if isinstance(history, list):
            normalized = []
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
                    normalized.append({
                        "type_code": code,
                        "buy": price_info["buy"],
                        "sell": price_info["sell"],
                        "update_time": int(datetime.strptime(date_str, "%Y-%m-%d").timestamp()),
                    })
            return normalized

        # Fallback cho các định dạng khác
        for key in ("prices", "items", "history", "rows", "result", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if self._is_price_record(item)]

        return []

    # ── public API ───────────────────────────────────────────

    def parse(self, type_code: str, payload: dict) -> List[GoldPriceRecord]:
        """Nhận JSON payload, trả về danh sách GoldPriceRecord đã chuẩn hóa."""
        if not payload.get("success"):
            logger.warning("API returned success=false for type=%s", type_code)
            return []

        raw_records = self._extract_records(payload)
        # Chỉ giữ đúng type_code yêu cầu
        raw_records = [r for r in raw_records if r.get("type_code") == type_code]

        if not raw_records:
            logger.warning("No price records found for type=%s", type_code)
            return []

        brand, gold_type = TYPE_MAPPING.get(type_code, ("unknown", "unknown"))
        results = []

        for item in raw_records:
            ts = datetime.fromtimestamp(int(item["update_time"]))
            raw_buy = float(item.get("buy", 0) or 0)
            raw_sell = float(item.get("sell", 0) or 0)

            if type_code == "XAUUSD":
                price = raw_buy if raw_buy > 0 else raw_sell
                buy_price = sell_price = mid_price = price
                spread = 0.0
            else:
                buy_price = raw_buy
                sell_price = raw_sell
                mid_price = (buy_price + sell_price) / 2.0
                spread = sell_price - buy_price

            results.append(GoldPriceRecord(
                ts=ts,
                type_code=type_code,
                brand=brand,
                gold_type=gold_type,
                buy_price=buy_price,
                sell_price=sell_price,
                mid_price=mid_price,
                spread=spread,
            ))

        logger.info("Parsed %s records for type=%s", len(results), type_code)
        return results
