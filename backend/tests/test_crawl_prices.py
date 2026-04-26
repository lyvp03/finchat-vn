import os
import json
import sys
import io
import requests
from datetime import datetime
from pathlib import Path

# Fix encoding cho Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "https://www.vang.today/api/prices"
TYPE_CODES = ["SJL1L10", "SJ9999", "DOHNL", "DOHCML", "BTSJC", "XAUUSD"]

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
    # Trích xuất dữ liệu từ API payload dựa trên code trong gold_price_ingest.py
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
                    "change_buy": price_info.get("day_change_buy"),
                    "change_sell": price_info.get("day_change_sell"),
                    "update_time": int(datetime.strptime(date_str, "%Y-%m-%d").timestamp()),
                })
        return normalized_records
    return []

def transform(type_code: str, item: dict):
    brand, gold_type = TYPE_MAPPING.get(type_code, ("unknown", "unknown"))
    # Dùng string cho JSON serialize dễ dàng
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

def main():
    print("=== TEST CRAWL 6 LOẠI VÀNG TRONG 30 NGÀY ===")
    all_rows = []
    
    for code in TYPE_CODES:
        print(f"[*] Đang lấy dữ liệu cho {code}...")
        try:
            r = requests.get(API_BASE, params={"type": code, "days": 30}, timeout=10)
            r.raise_for_status()
            payload = r.json()
            
            records = _extract_records(payload)
            # Lọc riêng type_code hiện tại vì API trả về chung
            records = [r for r in records if r.get("type_code") == code]
            
            rows = [transform(code, item) for item in records]
            all_rows.extend(rows)
            print(f"  -> Lấy thành công {len(rows)} bản ghi.")
        except Exception as e:
            print(f"  [-] Lỗi: {e}")

    # Xuất ra JSON
    output_dir = Path(__file__).resolve().parents[2] / "data"
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / "raw_prices_test.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)
        
    print(f"\n[+] Đã lưu tổng cộng {len(all_rows)} bản ghi ra file: {out_file}")

if __name__ == "__main__":
    main()
