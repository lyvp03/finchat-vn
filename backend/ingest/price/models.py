from dataclasses import dataclass
from datetime import datetime


@dataclass
class GoldPriceRecord:
    """Đại diện cho một bản ghi giá vàng đã được chuẩn hóa."""
    ts: datetime = None
    type_code: str = ""
    brand: str = ""
    gold_type: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    mid_price: float = 0.0
    spread: float = 0.0
    source_site: str = "vang.today"


# Bảng ánh xạ type_code API -> (brand, gold_type) nội bộ
TYPE_MAPPING = {
    "SJL1L10": ("sjc", "mieng_sjc"),
    "SJ9999":  ("sjc", "nhan_sjc"),
    "DOHNL":   ("doji", "doji_hn"),
    "DOHCML":  ("doji", "doji_hcm"),
    "BTSJC":   ("btmc", "btmc_sjc"),
    "XAUUSD":  ("world", "xauusd"),
}

TYPE_CODES = list(TYPE_MAPPING.keys())

# Metadata cho chatbot / dashboard
TYPE_CODE_METADATA = {
    "SJL1L10": {"name": "SJC gold bar 1L-10L",  "market": "domestic", "unit": "VND/lượng"},
    "SJ9999":  {"name": "SJC 9999 ring gold",   "market": "domestic", "unit": "VND/lượng"},
    "DOHNL":   {"name": "DOJI Hanoi gold",       "market": "domestic", "unit": "VND/lượng"},
    "DOHCML":  {"name": "DOJI HCM gold",         "market": "domestic", "unit": "VND/lượng"},
    "BTSJC":   {"name": "BTMC SJC gold bar",     "market": "domestic", "unit": "VND/lượng"},
    "XAUUSD":  {"name": "Spot gold XAU/USD",     "market": "world",    "unit": "USD/oz"},
}
