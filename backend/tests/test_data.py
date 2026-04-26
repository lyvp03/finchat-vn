# backend/crawler/test_data.py
# --- Test 1: Giá cổ phiếu VN ---
from vnstock import stock_historical_data
df = stock_historical_data("VCB", "2024-01-01", "2024-12-31", "1D", "stock")
print("VCB OK:", df.shape)
print(df.tail(3))

# --- Test 2: Giá vàng quốc tế ---
import yfinance as yf
gold = yf.download("GC=F", start="2024-01-01", end="2024-12-31")
print("Gold OK:", gold.shape)
print(gold.tail(3))

# --- Test 3: Scrape thử 1 bài CafeF ---
import httpx
r = httpx.get("https://cafef.vn/thi-truong-chung-khoan.chn",
              headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
print("CafeF status:", r.status_code)