# Kế hoạch implement preprocessing `gold_news`

## 1. Mục tiêu

Mục tiêu của preprocessing là biến dữ liệu news đã crawl từ dạng raw/semi-raw thành dữ liệu đủ sạch để dùng cho:

- phân tích quan hệ giữa tin tức và giá vàng;
- vẽ biểu đồ trong notebook/dashboard;
- retrieve trong RAG/vector DB;
- chatbot trả lời các câu hỏi như “vì sao giá vàng tăng/giảm hôm nay?”.

Output cuối cùng cần cập nhật lại các field trong bảng `gold_news`:

```sql
symbols,
tags,
entities,
sentiment_score,
impact_score,
relevance_score,
content_hash,
title_hash,
is_duplicate,
quality_score,
is_relevant,
event_type,
updated_at
```

---

## 2. Nguyên tắc kiến trúc

Preprocessing không nên viết lẫn trong crawler. Crawler chỉ chịu trách nhiệm lấy dữ liệu. Preprocessing là bước sau ingest.

Cấu trúc đề xuất (theo pattern đã thiết lập trong project):

```text
backend/
├── utils/
│   └── news_processing.py          ← hàm thuần: clean_text, compute_quality,
│                                      compute_relevance, extract_symbols,
│                                      classify_event_type, compute_sentiment,
│                                      compute_impact... Không có DB, không side-effect.
│
├── preprocessing/
│   └── news_enrichment.py           ← orchestrator: đọc DB → gọi utils → ghi DB
│
├── ingest/
│   └── news/
│       ├── models.py                ← NewsArticle dataclass + generate_hashes()
│       └── repositories/
│           └── gold_news_repository.py
│
└── jobs/
    └── worker/
        └── main.py                  ← schedule preprocessing job
```

Quy tắc:

```text
utils/news_processing.py     → hàm thuần: transform, scoring, tagging (không DB)
preprocessing/news_enrichment.py → orchestrator: đọc DB → gọi utils → ghi DB
repositories/*.py             → query/update DB (bulk insert)
jobs/worker/main.py           → chạy pipeline theo schedule
```

> **Lưu ý:** Không tạo 10 file riêng lẻ cho MVP. Gom vào 2 file chính:
> `utils/news_processing.py` (hàm thuần) và `preprocessing/news_enrichment.py` (orchestrator).
> Khi nào module quá lớn mới tách ra.

---

## 3. Phase 0 — Audit dữ liệu hiện tại

### Mục tiêu

Hiểu chất lượng dữ liệu hiện tại trước khi sửa.

### Việc cần làm

Tạo script/notebook audit:

```text
analysis/notebooks/audit_gold_news.ipynb
```

hoặc script:

```text
backend/jobs/audit_gold_news_job.py
```

Cần thống kê:

- tổng số bài;
- số bài theo `source_name`;
- số bài theo `language`;
- số bài thiếu `title`;
- số bài thiếu `content`;
- số bài có `title = content`;
- số bài content quá ngắn;
- số bài thiếu `published_at`;
- số bài trùng `canonical_url`;
- số bài trùng `content_hash`;
- phân bố `relevance_score`, `quality_score`, `sentiment_score`.

### Output

File report đơn giản:

```text
analysis/reports/gold_news_audit.md
```

### Acceptance criteria

- Biết rõ nguồn nào nhiễu nhất.
- Biết tỷ lệ bài thiếu content.
- Biết các field nào đang cần tính lại.

---

## 4. Phase 1 — Clean text và chuẩn hóa dữ liệu

### Mục tiêu

Làm sạch các field text để các bước hash, dedupe, relevance, sentiment chạy ổn định.

### File cần implement

```text
backend/preprocessing/news/clean_text.py
```

### Function đề xuất

```python
def clean_text(text: str | None) -> str:
    ...


def clean_article(article: NewsArticle) -> NewsArticle:
    ...
```

### Logic cần xử lý

- convert `None` thành chuỗi rỗng;
- strip khoảng trắng đầu/cuối;
- normalize unicode;
- unescape HTML entities;
- remove tag HTML còn sót;
- normalize multiple spaces/newlines;
- remove boilerplate phổ biến;
- không xóa quá mạnh làm mất nội dung chính.

### Rule MVP

```text
clean_title   = clean_text(title)
clean_summary = clean_text(summary)
clean_content = clean_text(content)
```

Nếu `content` rỗng nhưng `summary` có dữ liệu, vẫn giữ bài nhưng đánh `quality_score` thấp hơn ở phase sau.

### Acceptance criteria

- Không còn text bị lỗi khoảng trắng quá nhiều.
- Không còn HTML tag rõ ràng trong content.
- Không làm mất title/content hợp lệ.

---

## 5. Phase 2 — Recompute hash và normalize URL

### Mục tiêu

Tạo hash ổn định sau khi text đã được clean để phục vụ dedupe.

### Nâng cấp `generate_hashes()` trong `models.py`

**Không tạo file mới.** Nâng cấp method `generate_hashes()` đã có trong `ingest/news/models.py`.

Logic mới sau clean:

```python
def generate_hashes(self):
    # Normalize URL
    if not self.canonical_url and self.url:
        self.canonical_url = self.url.split('?')[0].split('#')[0]

    # Title hash
    if self.title:
        self.title_hash = sha256(clean_text(self.title))

    # Content hash — fallback nếu content rỗng
    if self.content and len(self.content) >= 50:
        self.content_hash = sha256(clean_text(self.content))
    else:
        self.content_hash = sha256(clean_text(self.title) + clean_text(self.summary) + self.canonical_url)

    # ID từ canonical_url
    if self.canonical_url:
        self.id = sha256(self.canonical_url)
```

### Acceptance criteria

- Không còn `content_hash` null.
- Không còn `title_hash` null với bài có title.
- Các bài giống nhau sau khi clean có hash giống nhau.

---

## 6. Phase 3 — Dedupe

### Mục tiêu

Đánh dấu bài trùng để khi retrieve/analysis không bị lặp tin.

### File cần implement

```text
backend/preprocessing/news/dedupe.py
```

### Function đề xuất

```python
def mark_duplicates(articles: list[NewsArticle]) -> list[NewsArticle]:
    ...
```

Nếu kiểm tra với DB thì gọi repository, không viết SQL trực tiếp trong file này:

```python
repository.exists_by_url_or_hash(...)
```

### Rule dedupe MVP

Dedupe theo thứ tự:

```text
1. canonical_url trùng
2. content_hash trùng
3. title_hash trùng trong cùng ngày
4. title gần giống nhau trong cùng ngày, similarity >= 0.9 (dùng rapidfuzz)
```

### Dependency

```text
pip install rapidfuzz
```

Dùng `rapidfuzz.fuzz.ratio()` cho bước 4 — nhanh, chính xác, lightweight.

### Cách chọn bài giữ lại

Ưu tiên bài có:

```text
1. content dài hơn
2. source uy tín hơn
3. published_at sớm hơn
4. quality_score cao hơn, nếu đã có
```

Các bài còn lại set:

```text
is_duplicate = true
```

### Acceptance criteria

- Không xóa dữ liệu raw ngay ở MVP.
- Chỉ đánh dấu `is_duplicate`.
- Retrieval có thể filter `is_duplicate = false`.

---

## 7. Phase 4 — Quality score

### Mục tiêu

Đánh giá bài nào đủ chất lượng để dùng cho RAG/phân tích sâu.

### File cần implement

```text
backend/preprocessing/news/quality.py
```

### Function đề xuất

```python
def compute_quality_score(article: NewsArticle) -> float:
    ...
```

### Rule MVP đề xuất

Score từ `0.0` đến `1.0`.

**Bài có content đầy đủ (VnExpress, Kitco):**

```text
+0.20 nếu có title hợp lệ
+0.10 nếu có summary hợp lệ
+0.10 nếu có published_at hợp lệ
+0.10 nếu title khác content
+0.10 nếu source_name hợp lệ

Content length:
+0.40 nếu content_len >= 800
+0.25 nếu 200 <= content_len < 800
+0.10 nếu 50 <= content_len < 200
+0.00 nếu content_len < 50
```

**Bài Reuters (source_type == "rss", chỉ có title):**

Reuters không tham gia RAG sâu, dùng thang điểm riêng:

```text
Base score = 0.30 (thấp vì thiếu content)
+0.10 nếu title chứa keyword trực tiếp về vàng
+0.05 nếu title chứa keyword macro (Fed, CPI...)
+0.05 nếu có published_at hợp lệ
Max = 0.50
```

> Reuters quality_score tối đa 0.50 → không đủ ngưỡng embed vào vector DB
> nhưng vẫn dùng được cho analysis dashboard và sentiment overview.

Clamp về `[0.0, 1.0]`.

### Ngưỡng dùng

```text
quality_score < 0.35:
    không dùng cho phân tích sâu

quality_score >= 0.35:
    có thể dùng cho RAG cơ bản nếu relevance cao

quality_score >= 0.50:
    dùng tốt cho analysis
```

### Acceptance criteria

- Bài thiếu content bị score thấp.
- Bài `title = content` bị score thấp hơn.
- Bài dài, đầy đủ field có score cao.

---

## 8. Phase 5 — Relevance score và `is_relevant`

### Mục tiêu

Lọc tin thực sự liên quan đến vàng hoặc các yếu tố ảnh hưởng mạnh đến vàng.

### File cần implement

```text
backend/preprocessing/news/relevance.py
```

### Function đề xuất

```python
def compute_relevance_score(article: NewsArticle) -> float:
    ...


def is_relevant(score: float) -> bool:
    return score >= 0.35
```

### Nhóm keyword trực tiếp

```text
gold
xauusd
xau/usd
bullion
precious metal
spot gold
gold futures
giá vàng
vàng miếng
vàng nhẫn
SJC
DOJI
PNJ
Bảo Tín Minh Châu
```

### Nhóm keyword gián tiếp

```text
Fed
FOMC
interest rate
rate cut
rate hike
inflation
CPI
PCE
NFP
jobs report
USD
DXY
dollar
Treasury yield
bond yield
safe haven
geopolitical
war
conflict
tariff
trade war
recession
central bank
```

### Rule MVP

```text
Nếu title có keyword trực tiếp về vàng:
    +0.60

Nếu content/summary có keyword trực tiếp về vàng:
    +0.30

Nếu có macro keyword ảnh hưởng vàng:
    +0.10 đến +0.30

Nếu là bài có "Gold Card", "gold visa" nhưng không liên quan vàng hàng hóa:
    trừ mạnh hoặc set score thấp
```

Sau đó:

```text
relevance_score = min(score, 1.0)
is_relevant = relevance_score >= 0.35
```

### Acceptance criteria

- Reuters general business news không liên quan bị loại khỏi RAG.
- Tin vàng trực tiếp có score cao.
- Tin Fed/USD/CPI không nhắc vàng nhưng liên quan macro có score trung bình.

---

## 9. Phase 6 — Extract symbols, tags, entities

### Mục tiêu

Tạo metadata để query, filter, group và retrieve tốt hơn.

### File cần implement

```text
backend/preprocessing/news/entity_extract.py
```

### Function đề xuất

```python
def extract_symbols(article: NewsArticle) -> list[str]:
    ...


def extract_tags(article: NewsArticle) -> list[str]:
    ...


def extract_entities(article: NewsArticle) -> dict:
    ...
```

### Symbols đề xuất

```text
GOLD
XAUUSD
SJC
USD
DXY
US10Y
VND
PNJ
DOJI
BTMC
FED
CPI
PCE
NFP
```

### Tags đề xuất

```text
gold_price
domestic_gold
world_gold
sjc
gold_ring
fed
interest_rate
usd
dxy
inflation
cpi
pce
nfp
bond_yield
geopolitical
safe_haven
tariff
central_bank
stock_market
oil
crypto
```

### Entities format

Giữ `entities` là `List[str]` theo model hiện tại. Mỗi entity là một string đơn giản:

```python
entities: List[str] = ["Fed", "SJC", "USD", "gold", "Vietnam"]
```

Không dùng JSON nested object vì:
- Model hiện tại đã là `List[str]`
- ClickHouse schema là `Array(String)` — khớp trực tiếp
- Đơn giản hơn cho query filter

### Acceptance criteria

- Bài SJC có `symbols` chứa `SJC`, `GOLD`, `VND`.
- Bài XAUUSD có `symbols` chứa `XAUUSD`, `GOLD`, `USD`.
- Bài Fed có tag `fed`, `interest_rate` nếu phù hợp.

---

## 10. Phase 7 — Classify `event_type`

### Mục tiêu

Gán loại sự kiện chính cho bài news để chatbot giải thích nguyên nhân biến động giá.

### File cần implement

```text
backend/preprocessing/news/event_type.py
```

### Function đề xuất

```python
def classify_event_type(article: NewsArticle) -> str:
    ...
```

### Event type MVP

```text
gold_price_update
fed_policy
inflation_data
usd_movement
bond_yield
geopolitical_risk
tariff_trade
domestic_market
central_bank_demand
economic_growth
stock_market_risk
other
```

### Rule MVP

```text
Có SJC / vàng nhẫn / DOJI / PNJ / trong nước:
    domestic_market

Có gold price / spot gold / bullion / gold futures:
    gold_price_update

Có Fed / FOMC / rate cut / rate hike / interest rate:
    fed_policy

Có CPI / PCE / inflation:
    inflation_data

Có USD / dollar / DXY:
    usd_movement

Có yield / Treasury:
    bond_yield

Có war / conflict / geopolitical / safe haven:
    geopolitical_risk

Có tariff / trade war:
    tariff_trade

Có central bank buying gold:
    central_bank_demand
```

### Acceptance criteria

- Không để `event_type` trống.
- Bài không phân loại được thì set `other`.
- Event type đủ tốt để group theo ngày/tháng.

---

## 11. Phase 8 — Sentiment score

### Mục tiêu

Đánh giá bài news bullish/bearish cho giá vàng.

### File cần implement

```text
backend/preprocessing/news/sentiment.py
```

### Function đề xuất

```python
def compute_sentiment_score(article: NewsArticle) -> float:
    ...
```

### Scale

```text
-1.0 = bearish cho vàng
 0.0 = trung tính
+1.0 = bullish cho vàng
```

### Rule bullish cho vàng

```text
vàng tăng / gold rises / gold gains
rate cut / dovish Fed
USD weakens / dollar falls
Treasury yield falls
dicey economy / recession risk
geopolitical risk / war / conflict
safe haven demand
inflation concern
central bank buying gold
```

### Rule bearish cho vàng

```text
vàng giảm / gold falls / gold slips
rate hike / hawkish Fed
USD strengthens / dollar rises
Treasury yield rises
risk-on sentiment
inflation cools làm giảm kỳ vọng cắt lãi
```

### MVP approach

Ban đầu dùng rule-based keyword. Sau đó nếu cần mới nâng cấp bằng LLM classifier.

### Acceptance criteria

- Tin “gold rises” score dương.
- Tin “gold falls” score âm.
- Tin macro không rõ chiều score gần 0.

---

## 12. Phase 9 — Impact score

### Mục tiêu

Đánh giá mức độ có khả năng ảnh hưởng đến giá vàng.

### File cần implement

```text
backend/preprocessing/news/impact.py
```

### Function đề xuất

```python
def compute_impact_score(article: NewsArticle) -> float:
    ...
```

### Scale

```text
0.0 = gần như không ảnh hưởng
1.0 = ảnh hưởng mạnh
```

### Rule MVP

```text
Fed / CPI / PCE / NFP / USD / DXY / US yields:
    0.70–1.00

Tin vàng trực tiếp:
    0.60–0.90

Tin địa chính trị / safe haven:
    0.60–0.90

Tin domestic gold/SJC:
    0.50–0.80

Tin kinh tế chung không nhắc vàng:
    0.20–0.50

Tin không liên quan:
    0.00–0.20
```

### Acceptance criteria

- `impact_score` không giống `sentiment_score`.
- Tin Fed/CPI/NFP được impact cao.
- Tin không liên quan có impact thấp.

---

## 13. Phase 10 — Save enriched data về DB

### Mục tiêu

Update lại bảng `gold_news` sau preprocessing.

### Cách implement: Bulk Insert (không dùng ReplacingMergeTree merge)

Bổ sung method vào `gold_news_repository.py`:

```python
def save_enriched_bulk(self, articles: list[NewsArticle]) -> bool:
    """Bulk insert lại toàn bộ row đã enriched với updated_at mới.
    ReplacingMergeTree sẽ tự gộp row cũ theo id khi merge."""
    ...
```

Luồng xử lý:

```text
1. Đọc batch bài chưa enrich từ DB
2. Chạy pipeline enrichment (clean → hash → quality → relevance → ...)
3. Bulk insert toàn bộ batch đã enrich (cùng id, updated_at mới)
4. ClickHouse background merge sẽ tự loại row cũ
```

> **Quan trọng:** Dùng `save_bulk()` hiện có — đã hỗ trợ bulk insert.
> Không cần UPDATE SQL hay ALTER mutation.
> Chỉ cần đảm bảo `id` giữ nguyên và `updated_at` mới hơn.

### Field cần update

```text
title           (sau clean)
summary         (sau clean)
content         (sau clean)
canonical_url   (sau normalize)
content_hash    (recompute sau clean)
title_hash      (recompute sau clean)
is_duplicate
quality_score
relevance_score
is_relevant
symbols
tags
entities
event_type
sentiment_score
impact_score
updated_at      (set datetime.now())
```

### Acceptance criteria

- Chạy pipeline nhiều lần không tạo dữ liệu sai.
- Row enriched có `updated_at` mới hơn row raw.
- Query `is_relevant = true` trả ra bài hợp lý.
- Dùng bulk insert, không dùng row-by-row UPDATE.

---

## 14. Phase 11 — Embed vào vector DB

### Mục tiêu

Chỉ đưa bài đủ tốt vào vector DB để chatbot retrieve.

### Rule chọn bài embed

```text
is_relevant = true
quality_score >= 0.35
is_duplicate = false
```

Có thể dùng ngưỡng cao hơn nếu data nhiễu:

```text
quality_score >= 0.50
relevance_score >= 0.50
```

### Metadata cần lưu trong vector DB

```text
article_id
title
source_name
published_at
url
symbols
tags
event_type
sentiment_score
impact_score
relevance_score
quality_score
language
```

### Acceptance criteria

- Không embed bài không liên quan.
- Không embed duplicate.
- Retrieve câu hỏi về vàng không kéo về bài “Gold Card visa” hoặc business news nhiễu.

---

## 15. Phase 12 — Notebook analysis sau preprocessing

### Mục tiêu

Dùng dữ liệu enriched để phân tích và vẽ biểu đồ.

### Notebook đề xuất

```text
analysis/notebooks/gold_news_price_analysis.ipynb
```

### Analysis cần làm

- phân bố số bài theo ngày;
- phân bố số bài theo source;
- top event_type theo tuần/tháng;
- sentiment trung bình theo ngày;
- impact trung bình theo ngày;
- join với `gold_prices_daily`;
- đánh dấu ngày giá biến động mạnh;
- lấy top news quanh ngày biến động ±1 đến ±3 ngày;
- vẽ giá + MA + marker event.

### Acceptance criteria

- Có thể trả lời câu: ngày nào giá biến động mạnh và news nào liên quan.
- Có biểu đồ giá vàng kèm event/news marker.

---

## 16. Phase 13 — Test

### Unit tests

Tạo folder:

```text
tests/preprocessing/news/
```

Test các module:

```text
test_clean_text.py
test_hash_news.py
test_quality.py
test_relevance.py
test_entity_extract.py
test_event_type.py
test_sentiment.py
test_impact.py
```

### Test cases quan trọng

```text
1. Content null không làm pipeline crash.
2. Title null không làm pipeline crash.
3. Bài SJC được relevant cao.
4. Bài Reuters business không liên quan bị relevant thấp.
5. Bài Gold Card visa không bị nhận nhầm là vàng.
6. Bài gold rises có sentiment dương.
7. Bài gold falls có sentiment âm.
8. Bài Fed/CPI/NFP có impact cao.
9. Duplicate URL được mark duplicate.
10. Hash ổn định sau clean.
```

---

## 17. Thứ tự implement khuyến nghị

### Sprint 1 — Làm sạch và lọc nhiễu

```text
1. utils/news_processing.py — implement clean_text, compute_quality, compute_relevance
2. Nâng cấp models.py generate_hashes() (hash sau clean, fallback logic)
3. preprocessing/news_enrichment.py — orchestrator bản đơn giản
4. Bulk insert enriched data về DB
5. Thêm job_preprocess_news vào jobs/worker/main.py (chạy mỗi 1 giờ)
```

Kết quả sprint 1:

```text
Dữ liệu có clean text, hash, quality_score, relevance_score, is_relevant.
```

### Sprint 2 — Metadata phục vụ phân tích

```text
1. Thêm extract_symbols, extract_tags, extract_entities vào utils/news_processing.py
2. Thêm classify_event_type vào utils/news_processing.py
3. Thêm mark_duplicates (dùng rapidfuzz) vào utils/news_processing.py
4. Update orchestrator news_enrichment.py
5. Viết audit report sau preprocessing
```

Kết quả sprint 2:

```text
Có symbols, tags, entities, event_type, is_duplicate.
```

### Sprint 3 — Scoring nâng cao và RAG

```text
1. Thêm compute_sentiment, compute_impact vào utils/news_processing.py
2. Update orchestrator news_enrichment.py
3. embed_news_job.py — chỉ embed bài is_relevant=true, quality>=0.50, is_duplicate=false
4. Vector DB metadata
5. Retrieval smoke test
```

Kết quả sprint 3:

```text
News đủ metadata để chatbot retrieve và giải thích biến động giá.
```

### Sprint 4 — Notebook analysis

```text
1. join news với gold_prices_daily
2. detect ngày biến động mạnh
3. vẽ biểu đồ giá + event marker
4. tạo insight mẫu cho chatbot
```

Kết quả sprint 4:

```text
Có notebook phân tích và biểu đồ demo.
```

---

## 18. Pipeline tổng thể

```text
raw gold_news
   ↓
clean text
   ↓
normalize URL + recompute hash
   ↓
dedupe
   ↓
quality_score
   ↓
relevance_score + is_relevant
   ↓
symbols / tags / entities
   ↓
event_type
   ↓
sentiment_score
   ↓
impact_score
   ↓
update gold_news
   ↓
embed relevant high-quality news
   ↓
notebook analysis / chatbot RAG
```

---

## 19. MVP definition of done

Preprocessing được xem là đạt MVP khi:

```text
1. Không còn content_hash null với bài hợp lệ.
2. Mỗi bài có quality_score.
3. Mỗi bài có relevance_score.
4. is_relevant không còn default true toàn bộ.
5. Reuters general news không liên quan bị lọc.
6. Mỗi bài có event_type, ít nhất là other.
7. Bài liên quan vàng có symbols/tags đúng cơ bản.
8. Chỉ bài is_relevant=true và quality_score đủ tốt mới được embed.
9. Notebook có thể query top news theo ngày biến động giá.
```

---

## 20. Gợi ý config threshold

Nên để threshold trong config, không hard-code rải rác.

```python
NEWS_RELEVANCE_THRESHOLD = 0.35
NEWS_EMBED_MIN_QUALITY = 0.35
NEWS_ANALYSIS_MIN_QUALITY = 0.50
NEWS_DUP_TITLE_SIMILARITY = 0.90
```

Có thể đặt trong:

```text
backend/core/config.py
```

hoặc:

```text
backend/preprocessing/news/config.py
```

---

## 21. Lưu ý riêng cho data hiện tại

Data hiện tại có 3 nguồn chính:

```text
VnExpress
Reuters
Kitco
```

Reuters là nguồn dễ nhiễu nhất vì có nhiều tin business/macro không trực tiếp liên quan vàng. Vì vậy trong MVP cần ưu tiên làm tốt:

```text
relevance.py
event_type.py
quality.py
```

Không nên bỏ Reuters, vì Reuters hữu ích cho tin macro như Fed, USD, CPI, yield, địa chính trị. Nhưng bắt buộc phải lọc bằng `relevance_score` trước khi đưa vào RAG hoặc phân tích.
