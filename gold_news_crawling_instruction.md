# Gold News Crawling Instruction

## Mục tiêu

Xây dựng module crawl tin tức vàng cho 3 nguồn dữ liệu sau:

1. Reuters Gold
2. Kitco News
3. VnExpress - Giá vàng / Giá vàng thế giới

Mục tiêu của crawler là thu thập bài viết mới và backfill lịch sử, chuẩn hóa dữ liệu theo đúng schema bảng `gold_news`, loại bỏ bản ghi trùng lặp cơ bản, và lưu raw payload để phục vụ debug hoặc reprocess.

Bảng đích đã được chốt như sau:

```sql
CREATE TABLE IF NOT EXISTS gold_news (
    id String,

    title String,
    summary String,
    content String,

    source_name String,
    source_type String,
    author String,
    url String,
    canonical_url String,

    published_at DateTime,
    crawled_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now(),

    category String,
    language String DEFAULT 'vi',
    region String,
    event_type String,

    symbols Array(String),
    tags Array(String),
    entities String,

    sentiment_score Nullable(Float32),
    impact_score Nullable(Float32),
    relevance_score Nullable(Float32),

    content_hash String,
    title_hash String,
    is_duplicate Bool DEFAULT false,
    quality_score Nullable(Float32),
    is_relevant Bool DEFAULT true,

    raw_payload String,
    extra_metadata String
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (id)
```

---

## Phạm vi công việc

Crawler cần hỗ trợ 2 mode:

### 1. Backfill
- Crawl dữ liệu lịch sử từ seed URLs hoặc archive/listing pages
- Có tham số `start_date`, `end_date`
- Chỉ lấy bài trong khoảng thời gian yêu cầu

### 2. Incremental
- Crawl định kỳ các bài mới nhất
- Kiểm tra trùng lặp theo `url`, `canonical_url`, `content_hash`, `title_hash`
- Không tạo bản ghi mới nếu bài viết đã tồn tại và không thay đổi nội dung

---

## 3 nguồn cần crawl

## 1) Reuters Gold
### Mục tiêu
Lấy tin quốc tế liên quan trực tiếp đến:
- giá vàng thế giới
- Fed, lãi suất, CPI, NFP
- USD, lợi suất trái phiếu
- chiến sự, địa chính trị
- ETF gold flows, central bank buying

### Gán metadata mặc định
- `source_name`: `"reuters"`
- `source_type`: `"web"`
- `category`: `"macro_gold"`
- `language`: `"en"`
- `region`: `"global"`

### Kỳ vọng parse được
- title
- summary nếu có
- content đầy đủ của bài
- author nếu có
- published_at
- canonical_url

### Lưu ý
- Reuters thường có listing page và article page riêng
- Ưu tiên lấy từ listing page trước, sau đó vào từng article page để parse body
- Nếu article body không parse được đầy đủ thì vẫn lưu title + summary + metadata, nhưng đánh `quality_score` thấp hơn

---

## 2) Kitco News
### Mục tiêu
Lấy tin chuyên sâu về vàng và precious metals:
- gold outlook
- analyst commentary
- precious metals market recap
- macro commentary liên quan vàng

### Gán metadata mặc định
- `source_name`: `"kitco"`
- `source_type`: `"web"`
- `category`: `"gold_analysis"`
- `language`: `"en"`
- `region`: `"global"`

### Kỳ vọng parse được
- title
- summary hoặc excerpt nếu có
- content
- author
- published_at
- canonical_url

### Lưu ý
- Kitco có thể có bài opinion / analysis / market wrap
- Không cần cố phân biệt quá sâu ở crawler phase, có thể đưa thêm vào `tags` hoặc `extra_metadata`
- Nếu bài chỉ là snippet quá ngắn, vẫn có thể lưu nhưng `is_relevant` cần được đánh giá lại theo rule relevance

---

## 3) VnExpress - Giá vàng / Giá vàng thế giới
### Mục tiêu
Lấy tin trong nước và bản tin thị trường vàng phục vụ các use case:
- giá SJC
- vàng nhẫn
- giá vàng thế giới và trong nước
- chênh lệch nội địa - quốc tế
- chính sách quản lý vàng, NHNN
- nhu cầu mua bán trong nước

### Gán metadata mặc định
- `source_name`: `"vnexpress"`
- `source_type`: `"web"`
- `category`: `"domestic_gold"`
- `language`: `"vi"`
- `region`: `"vn"`

### Kỳ vọng parse được
- title
- summary nếu có sapo
- content
- author nếu có
- published_at
- canonical_url

### Lưu ý
- Có thể crawl từ trang chủ đề hoặc listing page
- Nên parse cả bài về giá vàng trong nước và giá vàng thế giới nếu nằm trong chuyên mục liên quan
- Với bài chỉ nhắc vàng rất ít, có thể đánh `is_relevant = false`

---

## Output contract cho mỗi bản ghi

Mỗi article sau khi parse xong phải được normalize thành đúng cấu trúc dưới đây trước khi insert:

```json
{
  "id": "string",
  "title": "string",
  "summary": "string",
  "content": "string",
  "source_name": "string",
  "source_type": "string",
  "author": "string",
  "url": "string",
  "canonical_url": "string",
  "published_at": "datetime",
  "crawled_at": "datetime",
  "updated_at": "datetime",
  "category": "string",
  "language": "string",
  "region": "string",
  "event_type": "string",
  "symbols": ["XAUUSD"],
  "tags": ["gold", "fed"],
  "entities": "json-string",
  "sentiment_score": null,
  "impact_score": null,
  "relevance_score": null,
  "content_hash": "string",
  "title_hash": "string",
  "is_duplicate": false,
  "quality_score": null,
  "is_relevant": true,
  "raw_payload": "json-string",
  "extra_metadata": "json-string"
}
```

---

## Mapping field chi tiết

## 1. `id`
Sinh deterministic id để tránh insert trùng.
Ưu tiên:
- hash của `canonical_url` nếu có
- nếu không có thì hash của `source_name + url`
- khuyến nghị dùng SHA256 hoặc MD5 dạng hex string

Ví dụ:
- `id = sha256(source_name + "|" + canonical_url)`

## 2. `title`
- Bắt buộc không rỗng
- Trim whitespace
- Normalize khoảng trắng liên tiếp thành một space

## 3. `summary`
- Lấy từ excerpt / dek / sapo / meta description nếu có
- Nếu không có thì để chuỗi rỗng `""`

## 4. `content`
- Lấy full text của bài
- Loại bỏ script, ads, related links, caption không cần thiết, boilerplate
- Giữ xuống dòng hợp lý
- Không để HTML thô nếu không cần thiết
- Nếu parse thất bại thì có thể fallback sang text từ các thẻ paragraph chính

## 5. `source_name`
Chỉ nhận một trong 3 giá trị:
- `reuters`
- `kitco`
- `vnexpress`

## 6. `source_type`
Tạm thời cố định:
- `web`

## 7. `author`
- Lấy author nếu có
- Nếu không có thì để chuỗi rỗng `""`

## 8. `url`
- URL thực tế đã crawl

## 9. `canonical_url`
- Lấy từ canonical tag nếu có
- Nếu không có thì dùng `url`

## 10. `published_at`
- Parse về `DateTime`
- Nếu source có timezone thì normalize nhất quán trước khi insert
- Không dùng `crawled_at` thay cho `published_at` trừ khi hoàn toàn không parse được thời gian, và nếu fallback thì phải log warning

## 11. `crawled_at` / `updated_at`
- Gán thời điểm pipeline xử lý hiện tại

## 12. `category`
Map mặc định theo source:
- Reuters -> `macro_gold`
- Kitco -> `gold_analysis`
- VnExpress -> `domestic_gold`

Có thể override nếu detect được rõ hơn từ nội dung:
- `macro_gold`
- `gold_analysis`
- `domestic_gold`
- `policy`
- `geopolitics`

## 13. `language`
- Reuters, Kitco -> `en`
- VnExpress -> `vi`

## 14. `region`
- Reuters, Kitco -> `global`
- VnExpress -> `vn`

## 15. `event_type`
Không bắt buộc phải classify quá sâu trong v1.
Có thể set theo keyword rule-based:
- chứa `Fed`, `interest rate`, `FOMC` -> `fed`
- chứa `CPI`, `inflation` -> `cpi`
- chứa `NFP`, `payrolls` -> `nfp`
- chứa `SJC` -> `sjc_update`
- chứa `NHNN`, `Ngân hàng Nhà nước` -> `policy`
- nếu không match -> `general`

## 16. `symbols`
Rule-based extraction:
- mặc định nếu bài liên quan vàng -> thêm `XAUUSD`
- nếu nhắc USD index -> thêm `DXY`
- nếu nhắc Treasury yield / US 10-year -> thêm `US10Y`
- với tin trong nước có thể thêm `SJC` nếu cần như một symbol nội bộ

## 17. `tags`
Tag đơn giản theo keyword:
- `gold`
- `fed`
- `inflation`
- `cpi`
- `nfp`
- `usd`
- `yield`
- `geopolitics`
- `sjc`
- `nhnn`
- `domestic_market`

## 18. `entities`
Lưu dưới dạng JSON string.
Ví dụ:
```json
{
  "people": [],
  "organizations": ["Federal Reserve"],
  "locations": ["US"],
  "instruments": ["XAUUSD", "DXY"]
}
```

Nếu chưa có NER đầy đủ thì có thể lưu:
```json
{}
```

## 19. `sentiment_score`, `impact_score`, `relevance_score`
Trong v1 có thể để `NULL`.
Chỉ populate khi có enrichment step riêng.

## 20. `content_hash`
Hash của normalized content.
Dùng để phát hiện bài cập nhật nội dung hoặc bài trùng.

## 21. `title_hash`
Hash của normalized title.

## 22. `is_duplicate`
Set `true` nếu phát hiện trùng theo rule dedupe.
Tuy nhiên khuyến nghị skip insert với duplicate rõ ràng, thay vì lưu mọi duplicate.

## 23. `quality_score`
Rule gợi ý:
- 0.9 - 1.0: parse tốt, có title + published_at + content đầy đủ
- 0.6 - 0.8: thiếu summary hoặc author nhưng content tốt
- 0.3 - 0.5: content ngắn hoặc parse không hoàn chỉnh
- < 0.3: article lỗi, thiếu body nghiêm trọng

## 24. `is_relevant`
Set `true` nếu bài có liên quan vàng hoặc các yếu tố ảnh hưởng vàng.
Set `false` nếu bài match sai chủ đề hoặc nhắc vàng quá hời hợt.

## 25. `raw_payload`
Lưu JSON string của dữ liệu raw trước khi normalize.
Tùy source có thể lưu:
- raw listing item
- raw article HTML rút gọn
- raw parsed fields trước normalize

## 26. `extra_metadata`
JSON string cho metadata mở rộng.
Ví dụ:
```json
{
  "fetch_method": "requests_html",
  "parser_version": "v1",
  "listing_url": "https://...",
  "http_status": 200
}
```

---

## Rule dedupe

Ưu tiên thứ tự kiểm tra:

1. `canonical_url` trùng
2. `url` trùng
3. `content_hash` trùng hoàn toàn
4. `title_hash` trùng và `published_at` gần nhau

Logic đề xuất:
- Nếu `canonical_url` đã tồn tại -> duplicate
- Nếu `url` đã tồn tại -> duplicate
- Nếu `content_hash` trùng và cùng source -> duplicate
- Nếu `title_hash` trùng và chênh lệch thời gian publish rất nhỏ -> duplicate tiềm năng

Khi duplicate:
- Nếu nội dung mới hơn hoặc đầy đủ hơn, có thể update record cũ qua `ReplacingMergeTree(updated_at)`
- Nếu không có gì khác biệt, skip insert

---

## Rule relevance filter

Giữ bài nếu có ít nhất một trong các nhóm tín hiệu:

### Tín hiệu trực tiếp
- gold
- bullion
- XAUUSD
- precious metals
- giá vàng
- vàng nhẫn
- vàng miếng
- SJC

### Tín hiệu gián tiếp nhưng rất liên quan
- Fed
- lãi suất
- CPI
- inflation
- NFP
- USD
- DXY
- Treasury yield
- geopolitical tension

Nếu bài không có tín hiệu rõ và content rất ngắn thì:
- `is_relevant = false`

---

## Rule quality filter

Một article tối thiểu nên có:
- `title` không rỗng
- `url` không rỗng
- `published_at` parse được hoặc có fallback rõ ràng
- `content` dài hơn ngưỡng tối thiểu, ví dụ 200 ký tự

Nếu không đạt:
- vẫn có thể log vào pipeline
- nhưng không nên insert, hoặc insert với `quality_score` rất thấp tùy config

---

## Parsing guideline

## Listing page
Crawler nên hỗ trợ:
- lấy danh sách article links từ listing page
- tránh crawl lại link đã xử lý
- chuẩn hóa relative URL thành absolute URL
- giới hạn số trang hoặc số bài theo config

## Article page
Parser nên cố gắng tách:
- title
- summary
- author
- published_at
- content
- canonical_url

Nên có selector riêng cho từng source.
Không dùng một parser generic cho cả 3 nguồn nếu điều đó làm giảm độ chính xác.

---

## Error handling

Cần xử lý các trường hợp:
- timeout
- 403 / 404 / 5xx
- HTML thay đổi cấu trúc
- thiếu published_at
- content rỗng
- duplicate insert

Yêu cầu:
- log rõ source, url, loại lỗi
- không làm hỏng cả batch chỉ vì một bài lỗi
- có retry giới hạn cho lỗi mạng tạm thời

---

## Logging tối thiểu

Mỗi lần chạy nên log:
- source đang crawl
- số listing page đã quét
- số article links lấy được
- số bài parse thành công
- số bài duplicate
- số bài bị reject vì quality
- số bài bị reject vì relevance
- số bài insert/update thành công
- tổng thời gian xử lý

---

## Cấu trúc module gợi ý

```text
backend/
├── ingest/
│   ├── gold_news_ingest.py     <-- Pipeline Orchestrator (Main entry)
│   ├── news/
│   │   ├── sources/            <-- Cào HTML/JSON từ web
│   │   │   ├── vnexpress.py
│   │   │   ├── reuters.py
│   │   │   └── kitco.py
│   │   ├── parsers/            <-- Bóc tách HTML ra text
│   │   │   ├── vnexpress_parser.py
│   │   │   ├── reuters_parser.py
│   │   │   └── kitco_parser.py
│   │   ├── models.py           <-- Định nghĩa Data Class (Article)
│   │   ├── dedupe.py           <-- Logic chống trùng lặp
│   │   └── store.py            <-- Logic lưu vào ClickHouse
│   └── utils/
│       ├── hashing.py
│       └── text_utils.py
```

---

## Data normalization rules

- Normalize whitespace cho `title`, `summary`, `content`
- Strip tracking params khỏi URL nếu cần
- Parse datetime nhất quán
- Dùng UTF-8
- Loại bỏ HTML tags không cần thiết
- Convert `entities`, `raw_payload`, `extra_metadata` thành JSON string hợp lệ trước khi insert

---

## Insert strategy

Do bảng dùng `ReplacingMergeTree(updated_at)`, strategy đề xuất:
- với bản ghi mới -> insert bình thường
- với bản ghi đã có nhưng nội dung cập nhật -> insert version mới với `updated_at` mới hơn
- downstream query có thể dùng logic FINAL khi thật sự cần

Không phụ thuộc hoàn toàn vào engine để xử lý duplicate logic; vẫn cần dedupe ở application layer.

---

## Định nghĩa hoàn thành v1

Một implementation được coi là đạt v1 nếu:
1. Crawl được cả 3 nguồn
2. Parse được title, content, published_at, url cho phần lớn bài
3. Normalize đúng schema `gold_news`
4. Có dedupe cơ bản
5. Có relevance filter và quality filter cơ bản
6. Lưu được `raw_payload` và `extra_metadata`
7. Có thể chạy ở cả mode backfill và incremental

---

## Yêu cầu code quality

- Code tách riêng source fetcher và parser
- Không hard-code logic lẫn lộn trong một file lớn
- Có interface hoặc abstract base cho source crawler nếu phù hợp
- Có unit test cho:
  - normalize title/content
  - hash generation
  - dedupe rule
  - keyword tagging
  - event_type mapping
- Có integration test đơn giản cho parser từ sample HTML nếu có thể

---

## Ưu tiên triển khai

Thứ tự nên làm:
1. Xây parser và crawler cho VnExpress trước
2. Sau đó Reuters
3. Sau đó Kitco
4. Hoàn thiện normalize + dedupe + store
5. Thêm enrichment rule-based

Lý do:
- VnExpress thường dễ validate output hơn với ngữ cảnh bài vàng trong nước
- Reuters giúp bổ sung macro signals
- Kitco tăng chất lượng domain-specific coverage

---

## Ghi chú cuối

Bản v1 không cần:
- sentiment model thật
- impact scoring model thật
- NER phức tạp
- semantic chunking
- summarization bằng LLM

Chỉ cần crawl ổn định, parse sạch, dedupe được, và insert đúng schema.
Mọi enrichment nâng cao có thể tách thành bước sau khi ingest.
