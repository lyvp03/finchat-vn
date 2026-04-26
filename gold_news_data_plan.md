# Gold News — Kế hoạch xử lý dữ liệu

> Tổng hợp từ audit thực tế `gold_news_enriched.csv` (698 bài)
> và `gold_news_preprocessing_plan.md`.

---

## 1. Kết quả audit dữ liệu hiện tại

| Chỉ số | Giá trị |
|---|---|
| Tổng bài | 698 |
| VnExpress | 298 bài (tiếng Việt) |
| Reuters | 200 bài (tiếng Anh) |
| Kitco | 200 bài (tiếng Anh) |
| `is_relevant = True` | 489 / 698 (70%) |
| `is_duplicate = True` | 0 |
| `title == content` | **200 bài** (toàn bộ Reuters) |
| Relevant nhưng content < 100 ký tự | **261 bài** |
| `raw_payload` null | 698/698 (100%) |
| `extra_metadata` null | 698/698 (100%) |

Phân bố score:

| Score | Mean | Min | Max |
|---|---|---|---|
| quality_score | 0.672 | 0.200 | 1.000 |
| relevance_score | 0.632 | 0.000 | 1.000 |
| sentiment_score | 0.063 | -0.976 | 0.955 |
| impact_score | 0.486 | 0.072 | 0.850 |

Phân bố event_type:

| Event type | Số bài |
|---|---|
| domestic_market | 242 |
| gold_price_update | 174 |
| **other** | **93** (hầu hết Reuters bị misclassify) |
| fed_policy | 76 |
| geopolitical_risk | 46 |
| usd_movement | 27 |
| stock_market_risk | 15 |
| inflation_data | 12 |
| central_bank_demand | 11 |
| tariff_trade | 2 |

---

## 2. Vấn đề đã phát hiện

### Vấn đề 1 — Reuters không có content (nghiêm trọng nhất)

**Nguyên nhân:** Reuters crawl qua Google News RSS → chỉ có title trong content.

**Hậu quả:**
- 93 bài classify `event_type = other` vì thiếu content
- RAG retrieve bài rỗng
- Sentiment gần random

**Giải pháp:** Reuters bị chặn scraping hoàn toàn (DataDome 401). Đã thử `curl_cffi`, Google Cache, Arc API, Wayback Machine — tất cả đều bị chặn.

**Quyết định:** Giữ Reuters qua Google News RSS — chỉ dùng cho dashboard/overview sentiment, **không đưa vào RAG**. Filter RAG:
```python
(title != content) & (content_len > 200) & (quality_score >= 0.50)
```

---

### Vấn đề 2 — Sentiment không hiệu quả với tiếng Việt

**Nguyên nhân:** FinBERT chỉ train tiếng Anh. 298 bài VnExpress tokenize sai.

**Giải pháp đã chọn trong notebook:** Dùng 2 model:
- Tiếng Anh → `ProsusAI/finbert`
- Tiếng Việt → `cardiffnlp/twitter-xlm-roberta-base-sentiment`

**Quyết định cho production:** Giữ nguyên cách này. Không dùng googletrans vì:
- Multilingual model chạy local, không phụ thuộc API bên ngoài
- Tốc độ ổn định hơn translate → FinBERT (2 bước vs 1 bước)
- Đã validate trong notebook

---

### Vấn đề 3 — Chatbot thiên về thị trường VN

**Giải pháp:** Thêm field `market_scope`:
- `domestic` → SJC, DOJI, PNJ, VnExpress
- `international` → XAU/USD, Fed, Kitco, Reuters
- `mixed` → đề cập cả hai

RAG system prompt filter theo `market_scope` dựa trên intent câu hỏi.

---

### Vấn đề 4 — `raw_payload` và `extra_metadata` null 100%

Không xử lý trong MVP. Giữ field nhưng không logic.

---

## 3. Schema bổ sung

### Field mới: `market_scope`

```sql
ALTER TABLE gold_news ADD COLUMN IF NOT EXISTS market_scope String DEFAULT '';
```

### ClickHouse entities mismatch

DB schema hiện tại: `entities String` (single string).
Model Python: `entities: List[str]`.

**Quyết định:** Giữ model `List[str]`. Repository serialize thành JSON string khi insert:
```python
json.dumps(article.entities, ensure_ascii=False)  # ["Fed", "SJC", "USD"]
```

---

## 4. Kiến trúc xử lý

### Cấu trúc file (khớp với project hiện tại)

```
backend/
├── core/
│   └── config.py                   ← threshold, env vars
│
├── utils/
│   ├── indicators.py               ← (đã có) math thuần cho giá vàng
│   └── news_processing.py          ← (MỚI) hàm thuần cho news preprocessing
│
├── preprocessing/
│   ├── compute_indicators.py       ← (đã có) orchestrator giá vàng
│   └── news_enrichment.py          ← (MỚI) orchestrator news enrichment
│
├── ml/
│   └── sentiment.py                ← (MỚI) load FinBERT + multilingual model
│
├── ingest/
│   └── news/
│       ├── models.py               ← NewsArticle + generate_hashes() (nâng cấp)
│       ├── sources/                ← crawlers (đã có)
│       ├── parsers/                ← parsers (đã có)
│       ├── repositories/
│       │   └── gold_news_repository.py  ← thêm fetch_unenriched + save_enriched_bulk
│       └── services/               ← backfill + ingest (đã có)
│
└── jobs/
    └── worker/
        └── main.py                 ← thêm job_preprocess_news (mỗi 1 giờ)
```

### Quy tắc

```
utils/news_processing.py         → hàm thuần (input/output, không DB, không side-effect)
ml/sentiment.py                  → load model + score_text() — thuần inference
preprocessing/news_enrichment.py → orchestrator (đọc DB → gọi utils/ml → ghi DB)
```

---

## 5. Pipeline chi tiết

### Luồng tổng thể

```
raw gold_news
   ↓
[1] clean_text (title, summary, content)
   ↓
[2] generate_hashes (canonical_url, title_hash, content_hash, id)
   ↓
[3] compute_quality_score
   ↓
[4] compute_relevance_score + is_relevant
   ↓
[5] classify_market_scope
   ↓
[6] extract_symbols / extract_tags / extract_entities
   ↓
[7] classify_event_type
   ↓
[8] compute_sentiment (FinBERT EN / multilingual VI)
   ↓
[9] compute_impact_score
   ↓
[10] mark_duplicates (rapidfuzz title similarity >= 0.90)
   ↓
[11] bulk insert lại DB (cùng id, updated_at mới)
```

### Filter bài vào RAG

```python
is_relevant == True
AND is_duplicate == False
AND title != content
AND len(content) > 200
AND quality_score >= 0.50
```

---

## 6. Implement từng module

### 6.1 `utils/news_processing.py` — hàm thuần

Tất cả hàm sau đã được validate trong notebook, chuyển 1:1:

```python
# Từ notebook audit — đã test trên 698 bài
clean_text(text) -> str
compute_quality_score(article) -> float       # có Reuters RSS rule riêng
compute_relevance_score(article) -> float     # có noise filter (gold card, gold visa...)
classify_market_scope(article) -> str         # domestic/international/mixed
extract_symbols(article) -> List[str]
extract_tags(article) -> List[str]
extract_entities(article) -> List[str]
classify_event_type(article) -> str           # dùng v2 từ notebook
compute_impact_score(article) -> float
```

### 6.2 `ml/sentiment.py` — model loader + gold adjustment

FinBERT/multilingual model đo sentiment tài chính chung, không phải sentiment cho vàng.
Ví dụ: "USD strengthens" → FinBERT nói positive, nhưng với vàng là bearish.
Cần post-processing rules để điều chỉnh chiều.

```python
# Load 2 model:
# EN: ProsusAI/finbert
# VI: cardiffnlp/twitter-xlm-roberta-base-sentiment

def score_sentiment(text: str, language: str = "en") -> float:
    """Trả về float [-1.0, 1.0] từ góc nhìn giá vàng."""
    if language == "vi":
        raw_score = _multilingual_score(text[:512])
    else:
        raw_score = _finbert_score(text[:512])

    return adjust_for_gold(text, raw_score)
```

#### Gold-specific sentiment rules

Sau khi có raw score từ model, điều chỉnh theo logic thị trường vàng:

```python
# Bullish cho vàng (score nên dương)
GOLD_BULLISH_SIGNALS = [
    "gold rises", "gold gains", "gold rallies", "gold surges",
    "vàng tăng", "giá vàng tăng",
    "rate cut", "cắt giảm lãi suất", "dovish",
    "dollar weakens", "dollar falls", "usd giảm",
    "inflation concern", "inflation rises", "lạm phát tăng",
    "safe haven demand", "trú ẩn an toàn",
    "geopolitical risk", "war escalat", "conflict",
    "central bank buy", "ngân hàng trung ương mua",
    "treasury yield falls", "lợi suất giảm",
    "recession fear", "economic slowdown",
]

# Bearish cho vàng (score nên âm)
GOLD_BEARISH_SIGNALS = [
    "gold falls", "gold slips", "gold drops", "gold declines",
    "vàng giảm", "giá vàng giảm",
    "rate hike", "tăng lãi suất", "hawkish",
    "dollar strengthens", "dollar rises", "usd tăng",
    "inflation cools", "inflation eases", "lạm phát giảm",
    "risk-on", "risk appetite",
    "treasury yield rises", "lợi suất tăng",
]

def adjust_for_gold(text: str, raw_score: float) -> float:
    text_lower = text.lower()
    has_bullish = any(kw in text_lower for kw in GOLD_BULLISH_SIGNALS)
    has_bearish = any(kw in text_lower for kw in GOLD_BEARISH_SIGNALS)

    if has_bullish and not has_bearish:
        # Nếu model trả negative nhưng tin bullish cho vàng → đảo chiều
        return abs(raw_score) if raw_score < 0 else raw_score

    if has_bearish and not has_bullish:
        # Nếu model trả positive nhưng tin bearish cho vàng → đảo chiều
        return -abs(raw_score) if raw_score > 0 else raw_score

    # Cả hai hoặc không rõ → giữ nguyên model
    return raw_score
```

**Ví dụ:**

| Tin | Model raw | Gold rule | Final |
|---|---|---|---|
| "USD strengthens sharply" | +0.8 | bearish signal | **-0.8** |
| "Inflation rises to 4%" | -0.7 | bullish signal | **+0.7** |
| "Gold falls 2%" | -0.9 | bearish signal | **-0.9** (giữ nguyên) |
| "War escalates" | -0.8 | bullish signal | **+0.8** |

### 6.3 `preprocessing/news_enrichment.py` — orchestrator

```python
def enrich_batch(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Chạy toàn bộ pipeline trên 1 batch."""
    for article in articles:
        article.title = clean_text(article.title)
        article.summary = clean_text(article.summary)
        article.content = clean_text(article.content)
        article.generate_hashes()
        article.quality_score = compute_quality_score(article)
        article.relevance_score = compute_relevance_score(article)
        article.is_relevant = article.relevance_score >= RELEVANCE_THRESHOLD
        article.market_scope = classify_market_scope(article)
        article.symbols = extract_symbols(article)
        article.tags = extract_tags(article)
        article.entities = extract_entities(article)
        article.event_type = classify_event_type(article)
        article.sentiment_score = score_sentiment(
            f"{article.title}. {article.summary or ''}"[:512],
            language=article.language
        )  # score đã được adjust_for_gold() tự động
        article.impact_score = compute_impact_score(article)
        article.updated_at = datetime.now()
    return articles

def run_enrichment(batch_size=100):
    """Đọc bài chưa enrich → enrich → bulk insert lại."""
    client = get_clickhouse_client()
    repo = GoldNewsRepository(client)
    articles = repo.fetch_unenriched(limit=batch_size)
    if not articles:
        return
    enriched = enrich_batch(articles)
    enriched = mark_duplicates(enriched)  # rapidfuzz dedupe
    repo.save_bulk(enriched)
```

### 6.4 Nâng cấp `models.py`

Thêm field `market_scope`. Nâng cấp `generate_hashes()` với fallback khi content rỗng.

### 6.5 Nâng cấp `gold_news_repository.py`

Thêm method `fetch_unenriched()` — lấy bài chưa được enrich (chưa có market_scope, hoặc updated_at cũ).

---

## 7. Config & Threshold

Tất cả đặt trong `core/config.py`:

```python
# Relevance
NEWS_RELEVANCE_THRESHOLD      = 0.35

# Quality
NEWS_QUALITY_MIN_RAG          = 0.50
NEWS_QUALITY_MIN_ANALYSIS     = 0.35
NEWS_QUALITY_MAX_RSS_ONLY     = 0.50

# Dedupe
NEWS_DUP_TITLE_SIMILARITY     = 0.90

# RAG filter
RAG_MIN_CONTENT_LEN           = 200
RAG_EXCLUDE_TITLE_EQ_CONTENT  = True
```

---

## 8. Thứ tự implement

### Sprint 1 — Core preprocessing (utils + models + orchestrator)

Mục tiêu: Chuyển logic từ notebook sang production code.

```
1. utils/news_processing.py — chuyển tất cả hàm thuần từ notebook
2. ml/sentiment.py — load FinBERT + multilingual model
3. Nâng cấp models.py — thêm market_scope, nâng cấp generate_hashes()
4. Nâng cấp gold_news_repository.py — thêm fetch_unenriched()
5. preprocessing/news_enrichment.py — orchestrator
6. ALTER TABLE gold_news ADD COLUMN market_scope
7. Thêm config threshold vào core/config.py
8. Thêm job_preprocess_news vào worker (mỗi 1 giờ)
9. Chạy enrichment trên 698 bài hiện tại
```

Kết quả Sprint 1:
```
✓ Tất cả 698 bài có quality_score, relevance_score, market_scope,
  symbols, tags, entities, event_type, sentiment_score, impact_score
✓ event_type = 'other' < 10%
✓ Reuters quality max 0.50, không vào RAG
✓ Pipeline idempotent
```

### Sprint 2 — RAG & Chatbot

```
1. Filter bài đủ điều kiện → embed vào vector DB
2. Chatbot function calling với market_scope filter
3. System prompt phân biệt domestic/international
4. Test scenarios
```

### Sprint 3 — Thêm nguồn + Frontend

```
1. Thêm FXStreet/GoldPrice.org/CafeF nếu cần
2. Frontend hiển thị market_scope badge
3. Scheduler hoàn chỉnh
```

---

## 9. Definition of Done

Preprocessing MVP:

```
✓ Không còn bài title == content lọt vào RAG
✓ Sentiment đúng cả VI lẫn EN (2 model riêng)
✓ Mỗi bài có market_scope
✓ event_type = 'other' < 10%
✓ quality_score < 0.35 không vào RAG
✓ content < 200 ký tự không vào RAG
✓ Pipeline idempotent
```
