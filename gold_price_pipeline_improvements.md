# Gold Price Data Pipeline — Điểm cần cải thiện và ý nghĩa các chỉ số

## 1. Mục tiêu tài liệu

Tài liệu này tổng hợp các điểm cần cải thiện trong pipeline dữ liệu giá vàng sau khi chạy notebook phân tích `gold_price_analysis.ipynb`.

Mục tiêu chính:

- Làm dữ liệu giá vàng sạch hơn trước khi phân tích.
- Tránh sai lệch khi tính return, volatility, indicator và latest snapshot.
- Hiểu ý nghĩa từng chỉ số trong phân tích giá vàng.
- Chuẩn bị dữ liệu tốt hơn cho dashboard và chatbot phân tích vàng.

---

## 2. Vấn đề chính phát hiện trong dữ liệu hiện tại

### 2.1. Dữ liệu bị duplicate theo `ts + type_code`

Trong notebook, dữ liệu có:

```text
Total rows: 204
Unique timestamps: 31
Unique type_codes: 6
Duplicate rows by ts + type_code: 24
```

Nếu mỗi ngày có 6 loại giá, số dòng chuẩn nên là:

```text
31 days * 6 type_codes = 186 rows
```

Nhưng dữ liệu đang có 204 rows, nghĩa là đang dư dòng do crawl nhiều lần trong cùng một ngày.

### Vì sao vấn đề này nghiêm trọng?

Duplicate làm sai hoặc gây nhiễu cho:

- `daily_return_pct`
- `price_change`
- `latest_snapshot`
- technical indicators như `EMA`, `RSI`, `MACD`
- bảng `top_moves`
- correlation giữa các loại vàng
- export output cuối cùng

### Cách cải thiện

Sau khi load dữ liệu, cần dedupe theo:

```text
ts + type_code
```

Nếu có nhiều bản ghi cùng ngày và cùng loại vàng, giữ bản ghi mới nhất theo `created_at`.

```python
price_df["ts"] = pd.to_datetime(price_df["ts"], errors="coerce")
price_df["created_at"] = pd.to_datetime(price_df["created_at"], errors="coerce")

price_df = (
    price_df
    .sort_values(["ts", "type_code", "created_at"])
    .drop_duplicates(subset=["ts", "type_code"], keep="last")
    .reset_index(drop=True)
)

print("Rows after dedupe:", len(price_df))
print("Duplicate rows:", price_df.duplicated(["ts", "type_code"]).sum())
```

Kỳ vọng:

```text
Rows after dedupe: 186
Duplicate rows: 0
```

---

## 3. Các điểm cần cải thiện trong pipeline data price

## 3.1. Chuẩn hóa bước ingest dữ liệu giá

### Vấn đề

Hiện tại crawler có thể insert nhiều bản ghi cho cùng một `ts` và `type_code`.

Ví dụ:

```text
2026-04-23 + SJL1L10
2026-04-23 + XAUUSD
```

có thể xuất hiện nhiều lần nếu crawler chạy lại.

### Cải thiện

Trong pipeline ingest, cần có rule rõ:

```text
Một ngày + một type_code chỉ nên có một bản ghi daily chính thức.
```

Có 2 hướng:

### Option A — Lưu snapshot nhiều lần trong ngày

Nếu muốn crawl realtime nhiều phiên/ngày, nên dùng bảng riêng:

```text
gold_prices_intraday
```

Schema nên có:

```text
ts
crawl_time
type_code
buy_price
sell_price
mid_price
source
```

Sau đó aggregate ra bảng daily:

```text
gold_prices_daily
```

### Option B — Chỉ lưu daily final price

Nếu MVP chỉ cần phân tích theo ngày, mỗi ngày chỉ giữ bản ghi mới nhất:

```text
ORDER BY (ts, type_code)
ReplacingMergeTree(updated_at)
```

hoặc dedupe trước khi insert.

### Khuyến nghị MVP

Nên tách 2 tầng:

```text
raw/intraday price snapshots
        ↓
daily normalized price table
        ↓
analysis notebook / dashboard / chatbot
```

---

## 3.2. Tách rõ dữ liệu raw và dữ liệu cleaned

### Vấn đề

Nếu dùng trực tiếp file crawl raw để phân tích, notebook phải xử lý nhiều logic lặp lại: parse date, dedupe, compute return, validate missing.

### Cải thiện

Nên có 2 output:

```text
gold_price_raw.csv       # dữ liệu gốc từ crawler
gold_price_cleaned.csv   # dữ liệu đã chuẩn hóa để phân tích
```

Hoặc trong database:

```text
gold_prices_raw
gold_prices_daily
```

### Lợi ích

- Không mất dữ liệu gốc.
- Dễ debug lỗi crawler.
- Analysis luôn dùng bảng sạch.
- Chatbot không bị trả lời dựa trên dữ liệu duplicate.

---

## 3.3. Recompute indicators sau khi dedupe

### Vấn đề

CSV hiện tại đã có sẵn:

```text
ema20
ema50
rsi14
macd
macd_signal
macd_hist
```

Nhưng nếu các chỉ số này được tính trước khi dedupe, kết quả có thể bị lệch.

### Cải thiện

Sau khi dedupe và sort theo `ts`, nên recompute indicators trong notebook hoặc preprocessing job.

Thứ tự đúng:

```text
load raw data
↓
parse datetime
↓
dedupe by ts + type_code
↓
sort by type_code + ts
↓
compute return
↓
compute EMA / RSI / MACD
↓
export cleaned data
```

### Lý do

Technical indicators phụ thuộc vào chuỗi thời gian. Nếu chuỗi có duplicate hoặc sai thứ tự, indicator sẽ sai.

---

## 3.4. Không nên vẽ vàng trong nước và XAUUSD cùng raw scale

### Vấn đề

Giá vàng trong nước có đơn vị VND/lượng, khoảng hàng trăm triệu.

XAUUSD có đơn vị USD/oz, khoảng vài nghìn.

Nếu vẽ chung raw price trên một trục, XAUUSD sẽ bị ép sát đáy và biểu đồ khó đọc.

### Cải thiện

Nên dùng một trong ba cách:

### Cách 1 — Normalized index

Đặt giá đầu kỳ của mỗi loại vàng bằng 100:

```text
price_index = mid_price / first_mid_price * 100
```

Dùng để so sánh hiệu suất tương đối.

### Cách 2 — Vẽ riêng domestic và XAUUSD

```text
Chart 1: Domestic gold prices
Chart 2: XAUUSD price
```

### Cách 3 — Dual-axis chart

Một trục cho domestic, một trục cho XAUUSD. Cách này chỉ nên dùng nếu giải thích rõ để tránh hiểu nhầm.

---

## 3.5. Dùng `gold_news_enriched.csv` khi join với news

### Vấn đề

Notebook hiện tại có thể đang join với file news raw:

```text
gold_news.csv
```

File raw chưa có:

```text
sentiment_score
impact_score
relevance_score
is_relevant
event_type
```

Ngoài ra news raw có nhiều bài cũ như 2009, 2020, 2022, trong khi price data nằm trong khoảng 2026-03-24 đến 2026-04-23.

### Cải thiện

Nên join với:

```text
gold_news_enriched.csv
```

và filter theo window giá:

```python
news_filtered = news_filtered[
    (news_filtered["date"] >= price_clean["date"].min())
    & (news_filtered["date"] <= price_clean["date"].max())
]
```

### Lợi ích

Khi join news với price, có thể phân tích:

- ngày nào giá biến động mạnh;
- event_type nào xuất hiện nhiều;
- sentiment trung bình ngày đó là bullish hay bearish;
- impact trung bình ngày đó có cao không;
- top news nào giải thích biến động giá.

---

## 3.6. Tách threshold biến động cho domestic và XAUUSD

### Vấn đề

Notebook dùng threshold chung, ví dụ:

```text
abs(daily_return_pct) >= 1.0%
```

Nhưng XAUUSD thường biến động mạnh hơn vàng trong nước.

### Cải thiện

Nên dùng threshold riêng:

```text
Domestic gold: abs(return) >= 1.0%
XAUUSD: abs(return) >= 1.5% hoặc 2.0%
```

Hoặc dùng phương pháp thống kê:

```text
large_move = abs(return) > mean + 2 * std
```

### Lợi ích

Tránh việc XAUUSD tạo quá nhiều signal, còn domestic signal bị chìm.

---

## 3.7. Kiểm tra đơn vị giá và metadata từng `type_code`

### Vấn đề

Các mã như:

```text
BTSJC
DOHCML
DOHNL
SJ9999
SJL1L10
XAUUSD
```

cần được định nghĩa rõ. Nếu không, người đọc notebook hoặc chatbot khó giải thích.

### Cải thiện

Tạo mapping:

```python
TYPE_CODE_METADATA = {
    "BTSJC": {
        "name": "BTMC SJC gold bar",
        "market": "domestic",
        "unit": "VND/lượng",
    },
    "DOHCML": {
        "name": "DOJI HCM gold",
        "market": "domestic",
        "unit": "VND/lượng",
    },
    "DOHNL": {
        "name": "DOJI Hanoi gold",
        "market": "domestic",
        "unit": "VND/lượng",
    },
    "SJ9999": {
        "name": "SJC 9999 ring gold",
        "market": "domestic",
        "unit": "VND/lượng",
    },
    "SJL1L10": {
        "name": "SJC gold bar 1L-10L",
        "market": "domestic",
        "unit": "VND/lượng",
    },
    "XAUUSD": {
        "name": "Spot gold XAU/USD",
        "market": "world",
        "unit": "USD/oz",
    },
}
```

---

## 3.8. Latest snapshot phải chỉ có một dòng mỗi `type_code`

### Vấn đề

Latest snapshot hiện có nhiều hơn 6 dòng do duplicate ngày cuối.

### Cải thiện

Sau khi dedupe, latest snapshot phải có đúng:

```text
6 rows = 6 type_codes
```

Code:

```python
latest_date = price_clean["ts"].max()
latest_snapshot = price_clean[price_clean["ts"] == latest_date]

assert latest_snapshot["type_code"].nunique() == len(latest_snapshot)
```

### Lợi ích

Chatbot có thể trả lời chính xác:

```text
Giá mới nhất của từng loại vàng là bao nhiêu?
```

---

## 3.9. Tạo data quality checks tự động

### Cải thiện nên có trong pipeline

Mỗi lần ingest hoặc preprocess xong, nên kiểm tra:

```text
1. Không có duplicate ts + type_code
2. Không thiếu mid_price
3. buy_price <= sell_price
4. spread >= 0
5. daily_return_pct không vượt ngưỡng bất thường
6. Mỗi ngày có đủ số type_code kỳ vọng
7. Latest snapshot có đúng một dòng mỗi type_code
```

Ví dụ:

```python
assert price_clean.duplicated(["ts", "type_code"]).sum() == 0
assert price_clean["mid_price"].isna().sum() == 0
assert (price_clean["sell_price"] >= price_clean["buy_price"]).all()
assert (price_clean["spread"] >= 0).all()
```

---

## 4. Ý nghĩa các chỉ số trong notebook

## 4.1. `buy_price`

### Ý nghĩa

Giá doanh nghiệp mua vào từ khách hàng.

Nếu người dùng đang có vàng và muốn bán, họ thường nhận theo `buy_price`.

### Dùng để làm gì?

- So sánh giá bán ra của khách hàng.
- Tính spread giữa mua vào và bán ra.
- Đánh giá mức thiệt khi mua rồi bán ngay.

---

## 4.2. `sell_price`

### Ý nghĩa

Giá doanh nghiệp bán ra cho khách hàng.

Nếu người dùng muốn mua vàng, họ thường phải mua theo `sell_price`.

### Dùng để làm gì?

- Theo dõi giá mua thực tế của nhà đầu tư cá nhân.
- So sánh giữa các thương hiệu.
- Tính spread.

---

## 4.3. `mid_price`

### Ý nghĩa

Giá trung bình giữa mua vào và bán ra:

```text
mid_price = (buy_price + sell_price) / 2
```

### Dùng để làm gì?

`mid_price` là giá phù hợp nhất để phân tích trend vì nó nằm giữa bid và ask.

Dùng cho:

- price trend;
- daily return;
- EMA;
- RSI;
- MACD;
- correlation;
- volatility.

### Lưu ý

Không nên dùng `buy_price` hoặc `sell_price` riêng lẻ để tính trend nếu mục tiêu là phân tích thị trường chung.

---

## 4.4. `spread`

### Ý nghĩa

Chênh lệch giữa giá bán ra và giá mua vào:

```text
spread = sell_price - buy_price
```

### Nói lên điều gì?

Spread càng cao nghĩa là chi phí giao dịch càng lớn.

Ví dụ:

```text
buy_price = 170 triệu
sell_price = 173 triệu
spread = 3 triệu
```

Nếu mua xong bán lại ngay, người dùng có thể lỗ khoảng 3 triệu/lượng, chưa tính biến động giá.

### Dùng cho chatbot

Trả lời các câu như:

```text
Chênh lệch mua bán hiện có cao không?
Nên mua vàng lúc spread cao không?
Loại vàng nào có spread thấp hơn?
```

---

## 4.5. `spread_pct`

### Ý nghĩa

Spread tính theo phần trăm so với `mid_price`:

```text
spread_pct = spread / mid_price * 100
```

### Nói lên điều gì?

Giúp so sánh spread giữa các loại vàng có mức giá khác nhau.

Ví dụ:

```text
spread_pct = 1.8%
```

nghĩa là chênh lệch mua - bán bằng khoảng 1.8% giá trị vàng.

### Lưu ý

XAUUSD trong data hiện tại có `spread_pct = 0` vì source đang để `buy_price = sell_price`. Không nên kết luận rằng XAUUSD thực tế không có spread.

---

## 4.6. `price_change`

### Ý nghĩa

Mức thay đổi tuyệt đối của giá so với ngày trước:

```text
price_change = mid_price_today - mid_price_yesterday
```

### Nói lên điều gì?

Cho biết giá tăng/giảm bao nhiêu theo đơn vị gốc.

Ví dụ:

```text
SJC tăng 1.000.000 VND/lượng
XAUUSD giảm 50 USD/oz
```

### Lưu ý

Không nên so sánh trực tiếp `price_change` giữa domestic và XAUUSD vì khác đơn vị.

---

## 4.7. `daily_return_pct`

### Ý nghĩa

Tỷ lệ phần trăm thay đổi so với ngày trước:

```text
daily_return_pct = price_change / previous_mid_price * 100
```

### Nói lên điều gì?

Đây là chỉ số quan trọng để so sánh biến động giữa các loại vàng.

Ví dụ:

```text
SJC giảm 1.5%
XAUUSD tăng 3.6%
```

Có thể nói XAUUSD biến động mạnh hơn trong ngày đó.

### Dùng cho

- phát hiện ngày biến động mạnh;
- tính volatility;
- so sánh domestic và world gold;
- join với news để tìm nguyên nhân.

---

## 4.8. `volatility_pct`

### Ý nghĩa

Độ biến động của daily return, thường tính bằng standard deviation:

```text
volatility_pct = std(daily_return_pct)
```

### Nói lên điều gì?

Volatility càng cao nghĩa là giá dao động càng mạnh, rủi ro ngắn hạn càng lớn.

Trong kết quả notebook, XAUUSD có volatility cao hơn domestic gold. Điều này cho thấy vàng thế giới phản ứng nhanh và mạnh hơn với tin tức quốc tế.

---

## 4.9. `normalized price index`

### Ý nghĩa

Chuẩn hóa giá đầu kỳ về 100:

```text
price_index = mid_price / first_mid_price * 100
```

### Nói lên điều gì?

Cho biết mỗi loại vàng tăng/giảm bao nhiêu phần trăm so với đầu kỳ.

Ví dụ:

```text
price_index = 105
```

nghĩa là giá đã tăng 5% so với ngày đầu.

### Dùng cho

- so sánh domestic gold với XAUUSD;
- so sánh các loại vàng có đơn vị khác nhau;
- xem loại vàng nào outperform trong giai đoạn phân tích.

---

## 4.10. `EMA20` và `EMA50`

### Ý nghĩa

EMA là Exponential Moving Average, tức trung bình động lũy thừa.

```text
EMA20 = trung bình động 20 phiên
EMA50 = trung bình động 50 phiên
```

EMA phản ứng nhanh hơn SMA vì đặt trọng số lớn hơn cho dữ liệu gần hiện tại.

### Nói lên điều gì?

- Giá nằm trên EMA: xu hướng ngắn hạn tích cực hơn.
- Giá nằm dưới EMA: xu hướng ngắn hạn yếu hơn.
- EMA20 cắt lên EMA50: tín hiệu xu hướng tăng.
- EMA20 cắt xuống EMA50: tín hiệu xu hướng giảm.

### Lưu ý với dữ liệu hiện tại

Data chỉ có khoảng 31 ngày, nên EMA50 chưa thật sự đáng tin. EMA20 dùng được hơn EMA50 trong giai đoạn ngắn.

---

## 4.11. `RSI14`

### Ý nghĩa

RSI là Relative Strength Index, đo mức mạnh/yếu của biến động giá trong 14 phiên.

Scale:

```text
0 - 100
```

### Cách đọc phổ biến

```text
RSI > 70: có thể đang overbought
RSI < 30: có thể đang oversold
RSI 40-60: vùng trung tính
```

### Nói lên điều gì?

Nếu RSI thấp, giá đã giảm nhiều trong ngắn hạn và có thể đang bị bán quá mức.

Nếu RSI cao, giá đã tăng mạnh và có thể đang bị mua quá mức.

### Lưu ý

RSI không phải tín hiệu mua/bán độc lập. Cần kết hợp trend, news, spread và volatility.

---

## 4.12. `MACD`

### Ý nghĩa

MACD đo momentum của xu hướng, thường tính từ chênh lệch giữa EMA ngắn hạn và EMA dài hạn.

Các cột thường có:

```text
macd
macd_signal
macd_hist
```

### Cách đọc

```text
macd > macd_signal: momentum tích cực hơn
macd < macd_signal: momentum yếu hơn
macd_hist > 0: xu hướng tăng đang mạnh lên
macd_hist < 0: xu hướng giảm hoặc momentum yếu
```

### Nói lên điều gì?

MACD giúp nhận biết xu hướng đang tăng tốc hay suy yếu.

### Lưu ý

MACD cần chuỗi dữ liệu đủ dài. Với 31 ngày, MACD chỉ nên dùng như tín hiệu tham khảo.

---

## 4.13. `large_move`

### Ý nghĩa

Ngày có biến động mạnh, thường dựa vào `daily_return_pct`.

Ví dụ:

```text
large_move = abs(daily_return_pct) >= 1.0%
```

### Nói lên điều gì?

Đây là những ngày đáng chú ý để chatbot tìm nguyên nhân.

Ví dụ câu hỏi:

```text
Vì sao giá vàng giảm mạnh hôm đó?
Tin tức nào ảnh hưởng đến giá vàng ngày 2026-04-01?
```

### Cải thiện

Nên dùng threshold riêng cho domestic và XAUUSD hoặc dùng threshold thống kê.

---

## 4.14. `correlation`

### Ý nghĩa

Correlation đo mức độ hai chuỗi giá di chuyển cùng chiều hay ngược chiều.

Scale:

```text
+1: đi cùng chiều rất mạnh
 0: gần như không liên quan tuyến tính
-1: đi ngược chiều rất mạnh
```

### Nói lên điều gì?

Nếu domestic gold có correlation cao với nhau, nghĩa là các thương hiệu trong nước đi khá sát.

Nếu XAUUSD correlation chỉ trung bình với domestic gold, nghĩa là giá trong nước không phản ứng hoàn toàn 1-1 với thế giới.

### Insight từ notebook

- DOJI HCM và DOJI HN gần như giống nhau.
- Vàng trong nước tương quan cao với nhau.
- XAUUSD tương quan trung bình với vàng trong nước.

---

## 4.15. `latest_snapshot`

### Ý nghĩa

Bảng giá mới nhất của mỗi `type_code`.

Dùng để trả lời:

```text
Giá vàng mới nhất là bao nhiêu?
SJC hiện mua vào bán ra bao nhiêu?
XAUUSD hiện đang ở mức nào?
```

### Điều kiện đúng

Latest snapshot phải có đúng một dòng cho mỗi `type_code`.

Nếu có 6 type_code, latest snapshot phải có 6 rows.

Nếu nhiều hơn 6 rows, dữ liệu đang duplicate.

---

## 5. Pipeline đề xuất sau cải thiện

Pipeline nên đi theo luồng sau:

```text
crawl raw price
    ↓
save raw snapshot
    ↓
validate schema
    ↓
parse datetime
    ↓
dedupe by ts + type_code
    ↓
validate price fields
    ↓
compute mid_price / spread / spread_pct
    ↓
compute price_change / daily_return_pct
    ↓
compute EMA / RSI / MACD
    ↓
detect large moves
    ↓
join with enriched news
    ↓
export cleaned data + analysis outputs
    ↓
dashboard / chatbot
```

---

## 6. Definition of Done cho price pipeline MVP

Pipeline giá vàng được xem là đạt MVP khi:

```text
1. Không còn duplicate theo ts + type_code.
2. Không thiếu mid_price với các dòng hợp lệ.
3. buy_price <= sell_price.
4. spread >= 0.
5. latest_snapshot có đúng một dòng mỗi type_code.
6. daily_return_pct được tính sau khi dedupe.
7. EMA / RSI / MACD được tính sau khi dedupe.
8. Large move detection tách rõ domestic và XAUUSD.
9. Join news dùng gold_news_enriched.csv, không dùng raw news.
10. Export output sạch cho dashboard/chatbot.
```

---

## 7. Kết luận

Notebook phân tích giá vàng hiện tại đã đủ tốt cho MVP về mặt luồng phân tích. Tuy nhiên, pipeline data price cần cải thiện quan trọng nhất là xử lý duplicate trước khi tính toán.

Ba việc nên ưu tiên sửa trước:

```text
1. Dedupe theo ts + type_code, giữ bản ghi mới nhất theo created_at.
2. Recompute return và technical indicators sau dedupe.
3. Join với gold_news_enriched.csv và filter news theo date window của price data.
```

Sau khi sửa ba điểm này, dữ liệu giá sẽ đáng tin hơn để dùng cho phân tích, dashboard và chatbot giải thích biến động giá vàng.
