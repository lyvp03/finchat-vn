# Data Collection Plan for Gold RAG Chatbot

## 1. Mục tiêu

Mục tiêu của phase này là bổ sung đủ dữ liệu nền để chatbot không chỉ trả lời được **giá tăng/giảm**, mà còn có thể đánh giá **có đủ cơ sở để giải thích nguyên nhân hay chưa**.

Hiện tại hệ thống đã có:

- Giá vàng SJC trong nước.
- News retrieval từ Qdrant.
- LLM synthesis.
- Route dạng hybrid: price + news.

Vấn đề hiện tại:

- News gần đây còn ít.
- Tin retrieve được có thể chỉ là tin bối cảnh, không trực tiếp giải thích giá.
- LLM dễ suy diễn nguyên nhân nếu không có đủ evidence.
- Chưa có dữ liệu nền quan trọng như XAUUSD, USD/VND, premium trong nước - thế giới.

Vì vậy, ưu tiên không phải là thêm thật nhiều news ngay, mà là bổ sung các nhóm dữ liệu giúp hệ thống có evidence rõ hơn.

---

## 2. Nguyên tắc triển khai

### 2.1. Không để LLM tự suy luận khi thiếu evidence

LLM chỉ được tổng hợp dựa trên dữ liệu đã retrieve được. Nếu evidence chưa đủ, câu trả lời phải nói rõ:

```text
Hiện chưa đủ dữ liệu trực tiếp để kết luận nguyên nhân.
```

### 2.2. Structured data trước, news sau

Thứ tự ưu tiên:

```text
1. Giá vàng trong nước
2. Giá vàng thế giới / XAUUSD
3. Tỷ giá USD/VND
4. Chênh lệch trong nước - thế giới
5. News trực tiếp về giá vàng
6. News macro / quốc tế
```

Lý do: với bài toán phân tích giá vàng, dữ liệu giá và tỷ giá là evidence nền. News giúp giải thích thêm, nhưng nếu chỉ có news mà thiếu XAUUSD/USDVND thì LLM vẫn khó suy luận chắc.

---

## 3. Nhóm dữ liệu cần bổ sung

## 3.1. Domestic gold prices

### Mục tiêu

Không chỉ lưu SJC vàng miếng, mà cần thêm các loại vàng/thương hiệu khác để biết biến động là riêng SJC hay toàn thị trường.

### Dữ liệu cần có

- SJC vàng miếng.
- SJC vàng nhẫn.
- DOJI vàng miếng / vàng nhẫn.
- PNJ.
- Bảo Tín Minh Châu.
- Mi Hồng nếu nguồn hỗ trợ.

### Fields cần chuẩn hóa

```text
ts
type_code
brand
gold_type
buy_price
sell_price
mid_price
spread
source_site
crawled_at
```

### Mục đích phân tích

Hỗ trợ các câu hỏi:

```text
Giá SJC giảm có phải toàn thị trường cũng giảm không?
Vàng miếng và vàng nhẫn biến động khác nhau thế nào?
Spread mua bán hiện có cao không?
SJC đang lệch nhiều so với các thương hiệu khác không?
```

---

## 3.2. World gold price / XAUUSD

### Mục tiêu

Bổ sung giá vàng thế giới để so sánh với SJC.

### Dữ liệu cần có

```text
ts
symbol = XAUUSD
price / close
open
high
low
source_site
interval
crawled_at
```

### Interval đề xuất

MVP:

```text
hourly hoặc daily
```

Nếu chưa có hourly ổn định, bắt đầu với daily trước.

### Mục đích phân tích

Hỗ trợ các câu hỏi:

```text
Giá SJC giảm có cùng chiều với giá vàng thế giới không?
Giá vàng trong nước đang phản ứng theo thế giới hay đi ngược?
Biến động trong nước có bất thường so với XAUUSD không?
```

---

## 3.3. USD/VND exchange rate

### Mục tiêu

Bổ sung tỷ giá để quy đổi giá vàng thế giới sang VND/lượng.

### Dữ liệu cần có

```text
ts
symbol = USDVND
price
source_site
interval
crawled_at
```

Có thể mở rộng sau:

```text
USDVND ngân hàng
USD tự do / chợ đen
DXY
```

### Mục đích phân tích

Hỗ trợ:

```text
Quy đổi XAUUSD sang VND/lượng.
Tính premium SJC so với thế giới.
Giải thích ảnh hưởng của tỷ giá đến giá vàng trong nước.
```

---

## 3.4. Domestic-world premium

### Mục tiêu

Tạo bảng hoặc view derived để tính chênh lệch giữa giá SJC trong nước và giá vàng thế giới quy đổi.

### Công thức logic

```text
world_gold_vnd_per_luong = XAUUSD * USDVND * conversion_factor
premium = SJC_mid_price - world_gold_vnd_per_luong
premium_pct = premium / world_gold_vnd_per_luong
```

### Mục đích phân tích

Hỗ trợ:

```text
Chênh lệch giá vàng trong nước và thế giới đang là bao nhiêu?
Premium đang tăng hay giảm?
SJC có đang đắt bất thường so với thế giới không?
```

---

## 3.5. Direct gold news

### Mục tiêu

Bổ sung news trực tiếp nói về biến động giá vàng, thay vì chỉ các tin liên quan chung đến thị trường vàng.

### Loại tin cần ưu tiên

```text
SJC tăng/giảm.
Vàng miếng/vàng nhẫn tăng giảm.
Giá vàng trong nước so với thế giới.
Chênh lệch giá trong nước - thế giới.
Cung cầu vàng trong nước.
Người dân xếp hàng mua vàng.
Ngân hàng Nhà nước / chính sách vàng.
```

### Nguồn đề xuất sau khi pipeline ổn

```text
VnExpress hiện có.
CafeF.
Vietstock.
Tuổi Trẻ.
Lao Động.
VietnamFinance.
```

Không thêm nhiều nguồn cùng lúc. Mỗi lần chỉ thêm 1 nguồn, sau đó test dedup, relevance và retrieval.

---

## 3.6. Macro and international news

### Mục tiêu

Bổ sung bối cảnh quốc tế để giải thích biến động vàng thế giới.

### Chủ đề cần phân loại

```text
fed_policy
usd_movement
inflation_data
bond_yield
geopolitical_risk
central_bank_demand
economic_growth
stock_market_risk
```

### Nguồn đề xuất

```text
Reuters
Kitco
Investing
MarketWatch nếu lấy được
```

Lưu ý: nhóm này dễ noise. Cần relevance_score và event_type tốt trước khi index vào Qdrant.

---

## 4. Schema đề xuất

## 4.1. market_price

Dùng cho XAUUSD, USDVND, DXY, US10Y nếu mở rộng sau.

```sql
CREATE TABLE IF NOT EXISTS market_price (
    ts DateTime,
    symbol String,
    market String,
    price Float64,
    open Nullable(Float64),
    high Nullable(Float64),
    low Nullable(Float64),
    close Nullable(Float64),
    source_site String,
    interval String,
    crawled_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(crawled_at)
ORDER BY (symbol, ts);
```

### Symbol ban đầu

```text
XAUUSD
USDVND
```

### Symbol mở rộng sau

```text
DXY
US10Y
```

---

## 4.2. gold_price_premium

Bảng derived để tính chênh lệch trong nước - thế giới.

```sql
CREATE TABLE IF NOT EXISTS gold_price_premium (
    ts DateTime,
    domestic_type_code String,
    domestic_mid_price Float64,
    xauusd_price Float64,
    usd_vnd Float64,
    world_gold_vnd_per_luong Float64,
    premium Float64,
    premium_pct Float64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(calculated_at)
ORDER BY (domestic_type_code, ts);
```

---

## 4.3. Index tracking cho Qdrant

Nên có field hoặc bảng tracking để tránh index trùng và dễ re-index khi đổi chunking/embedding.

Có thể thêm vào pipeline metadata:

```text
indexed_at
embedding_model
chunking_version
vector_store
vector_collection
```

Nếu dùng bảng riêng:

```sql
CREATE TABLE IF NOT EXISTS news_vector_index_log (
    doc_id String,
    chunking_version String,
    embedding_model String,
    vector_store String,
    vector_collection String,
    indexed_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(indexed_at)
ORDER BY (doc_id, chunking_version, embedding_model, vector_collection);
```

---

## 5. Pipeline tổng thể

```text
Crawl structured market data
    -> clean / normalize
    -> store ClickHouse
    -> compute derived indicators / premium

Crawl news
    -> clean text
    -> dedup
    -> relevance scoring
    -> event type classification
    -> direct/contextual classification
    -> chunking
    -> embedding
    -> upsert Qdrant

User question
    -> resolve time range
    -> route intent
    -> query ClickHouse price / market data
    -> retrieve Qdrant news
    -> evidence grading
    -> LLM synthesis
```

---

## 6. Schedule đề xuất

## 6.1. Domestic gold price

MVP đơn giản:

```text
Mỗi 1 giờ từ 08:00 đến 17:00
```

Hoặc theo phiên thị trường:

```text
08:30
11:45
15:30
```

---

## 6.2. XAUUSD

MVP:

```text
Mỗi 1 giờ
```

Nếu chỉ lấy daily:

```text
08:00
15:30
21:00
```

---

## 6.3. USD/VND

```text
09:00
15:00
```

---

## 6.4. News crawl

```text
08:00
12:00
16:00
21:00
```

---

## 6.5. Preprocessing + Qdrant indexing

Chạy ngay sau mỗi news crawl:

```text
crawl news
-> preprocess
-> score
-> chunk
-> embed
-> upsert Qdrant
```

---

## 7. Evidence sufficiency layer

## 7.1. Mục tiêu

Trước khi gọi LLM, hệ thống cần biết dữ liệu hiện có đủ để giải thích nguyên nhân hay chưa.

## 7.2. Output đề xuất

```json
{
  "has_domestic_price": true,
  "has_world_gold": true,
  "has_usd_vnd": true,
  "has_direct_news": false,
  "direct_news_count": 0,
  "contextual_news_count": 1,
  "can_explain_cause": true,
  "confidence": "medium"
}
```

## 7.3. Rule gợi ý

### Chỉ có domestic price

```text
can_explain_cause = false
confidence = low
```

Trả lời được diễn biến giá, không kết luận nguyên nhân.

### Domestic price + contextual news

```text
can_explain_cause = false
confidence = low
```

Chỉ nói tin tức là bối cảnh, không gọi là nguyên nhân.

### Domestic price + XAUUSD + USD/VND

```text
can_explain_cause = true
confidence = medium
```

Có thể giải thích theo tương quan thị trường.

### Domestic price + XAUUSD + USD/VND + direct news

```text
can_explain_cause = true
confidence = high
```

Có thể đưa nhận định nguyên nhân rõ hơn, nhưng vẫn tránh khẳng định tuyệt đối.

---

## 8. Answer policy cho LLM

LLM phải tuân theo policy từ evidence grader.

### Nếu can_explain_cause = false

Không được viết:

```text
Nguyên nhân là...
Tin này khiến giá giảm...
```

Chỉ được viết:

```text
Dữ liệu hiện tại chưa đủ để kết luận nguyên nhân.
Tin này chỉ phản ánh bối cảnh liên quan.
```

### Nếu can_explain_cause = true và confidence = medium

Có thể viết:

```text
Biến động có thể liên quan đến...
Nhiều khả năng chịu ảnh hưởng từ...
```

### Nếu confidence = high

Có thể viết mạnh hơn nhưng vẫn có giới hạn:

```text
Các dữ liệu hiện có cho thấy nguyên nhân chính có thể đến từ...
```

---

## 9. Output format chuẩn

```text
1. Diễn biến giá
- Xu hướng:
- Mức thay đổi:
- Giá mới nhất:
- Tín hiệu kỹ thuật nếu có:

2. So sánh với thị trường thế giới
- XAUUSD:
- USD/VND:
- Premium trong nước - thế giới:

3. Tin tức liên quan
- Tin trực tiếp:
- Tin bối cảnh:

4. Nhận định tổng hợp
- Chỉ nhận định trong phạm vi evidence.
- Không suy diễn nếu dữ liệu thiếu.

5. Giới hạn dữ liệu
- Nêu rõ thiếu dữ liệu nào nếu có.
```

---

## 10. Phase implementation plan

## Phase 1: Add structured market data

### Tasks

```text
1. Tạo bảng market_price.
2. Viết crawler XAUUSD.
3. Viết crawler USD/VND.
4. Lưu vào ClickHouse.
5. Viết query lấy XAUUSD/USDVND theo time range.
```

### Test questions

```text
Giá vàng thế giới 7 ngày gần đây tăng hay giảm?
USD/VND biến động thế nào trong tuần qua?
Giá SJC giảm có cùng chiều với giá vàng thế giới không?
```

---

## Phase 2: Compute domestic-world premium

### Tasks

```text
1. Tính world_gold_vnd_per_luong.
2. Tính premium và premium_pct.
3. Lưu vào gold_price_premium hoặc tạo view.
4. Thêm query premium theo time range.
```

### Test questions

```text
Chênh lệch giá SJC với thế giới hiện là bao nhiêu?
Premium SJC tăng hay giảm trong 7 ngày gần đây?
Giá trong nước có đang lệch bất thường so với thế giới không?
```

---

## Phase 3: Improve news quality

### Tasks

```text
1. Thêm direct/contextual/weak classification.
2. Thêm min relevance threshold.
3. Không index bài is_relevant = false.
4. Không dùng weak news trong synthesis.
5. Nếu chỉ có contextual news, không kết luận nguyên nhân.
```

### Test questions

```text
Tin tức gần đây nói gì về giá vàng SJC?
Tin nào trực tiếp giải thích giá vàng SJC giảm?
Có tin nào chỉ là bối cảnh thị trường không?
```

---

## Phase 4: Evidence grader

### Tasks

```text
1. Tạo module evidence_grader.py.
2. Input: price_result, market_result, premium_result, news_result.
3. Output: can_explain_cause, confidence, reason.
4. Truyền output vào synthesis prompt.
```

### Test questions

```text
Tại sao giá vàng SJC giảm trong 7 ngày gần đây?
Giá SJC giảm có phải do giá thế giới giảm không?
Có đủ dữ liệu để kết luận nguyên nhân không?
```

---

## Phase 5: Add more news sources

Chỉ bắt đầu phase này sau khi phase 1-4 ổn.

### Tasks

```text
1. Thêm từng nguồn một.
2. Mapping source-specific fields về schema gold_news.
3. Clean/dedup.
4. Relevance scoring.
5. Event type classification.
6. Index Qdrant.
7. Test retrieval trước khi thêm nguồn tiếp theo.
```

### Nguồn ưu tiên

```text
1. CafeF hoặc Vietstock cho tin trong nước.
2. Kitco cho vàng quốc tế.
3. Reuters cho macro/global gold.
```

---

## 11. Definition of Done

Phase này được xem là hoàn thành khi chatbot có thể:

```text
1. Trả lời diễn biến SJC dựa trên ClickHouse.
2. So sánh SJC với XAUUSD và USD/VND.
3. Tính premium trong nước - thế giới.
4. Phân biệt tin trực tiếp và tin bối cảnh.
5. Không kết luận nguyên nhân khi evidence chưa đủ.
6. Nêu rõ giới hạn dữ liệu.
7. Trả lời các câu hỏi test mà không hallucinate.
```

---

## 12. Bộ câu hỏi test chính

```text
1. Giá vàng SJC 7 ngày gần đây tăng hay giảm?
2. Giá SJC giảm có cùng chiều với giá vàng thế giới không?
3. USD/VND biến động thế nào và có ảnh hưởng gì đến vàng trong nước không?
4. Chênh lệch giá SJC với thế giới hiện là bao nhiêu?
5. Tin tức gần đây nói gì về giá vàng SJC?
6. Có tin nào trực tiếp giải thích nguyên nhân giá SJC giảm không?
7. Nếu chỉ có tin bối cảnh, hệ thống có nói rõ chưa đủ dữ liệu không?
8. Giá vàng trong nước giảm là do thế giới giảm hay do yếu tố nội địa?
9. SJC có đang đắt bất thường so với giá vàng thế giới không?
10. Tóm tắt thị trường vàng trong 7 ngày gần đây dựa trên giá, XAUUSD, tỷ giá và tin tức.
```

---

## 13. Ưu tiên bắt đầu ngay

Thứ tự làm ngay:

```text
1. Tạo bảng market_price.
2. Crawl XAUUSD.
3. Crawl USD/VND.
4. Tính premium SJC vs world.
5. Thêm evidence_grader.
6. Sửa synthesis prompt theo can_explain_cause.
7. Sau đó mới thêm nguồn news mới.
```

Kết luận: để LLM suy luận tốt hơn, trước hết cần bổ sung dữ liệu nền. Với bài toán vàng Việt Nam, dữ liệu quan trọng nhất không phải chỉ là nhiều news hơn, mà là **SJC + XAUUSD + USD/VND + premium + direct news**.
