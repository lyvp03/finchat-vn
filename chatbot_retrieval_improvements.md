# Chatbot Retrieval & LLM Improvements Plan

## Tình trạng hiện tại

### Đã hoạt động

| Component | File | Status |
|---|---|---|
| LLM abstraction | `core/llm/` (Ollama + Gemini) | OK |
| Qdrant vector store | `rag/stores/qdrant_store.py` | OK, đã index chunks |
| Chunking | `rag/chunker.py` | OK, paragraph-windowed |
| Router | `chatbot/router.py` | OK, rule-based |
| Time range | `chatbot/time_range.py` | OK, 7 patterns |
| Price tool | `tools/price_tool.py` | OK, rolling + comparison |
| News tool | `tools/news_tool.py` | OK nhưng thiếu time filter |
| Context builder | `chatbot/context_builder.py` | OK nhưng đưa full articles |
| Orchestrator | `chatbot/orchestrator.py` | OK nhưng fallback dump raw JSON |
| Prompts | `chatbot/prompts.py` | OK |

### Vấn đề phát hiện

1. **News retrieval không filter theo thời gian** — `search_news()` không truyền `published_from_ts`/`published_to_ts` → Qdrant trả bài từ 2005, 2020 khi hỏi "7 ngày gần đây"
2. **Full article document vào LLM** — 5 bài × full content → context quá dài → Ollama local timeout
3. **Fallback answer dump raw JSON** — user thấy `str(price)` = JSON object dài
4. **Ollama qwen2.5:7b nặng** — 7B local chậm, cần chuyển sang model cloud free nhẹ hơn

---

## Thứ tự implement

```
1. Temporal filter cho news retrieval         ← fix chính xác kết quả
2. Compact news context trước khi đưa LLM    ← fix timeout
3. Fallback answer readable                   ← UX khi LLM lỗi
4. Chuyển sang Ollama cloud-free model        ← tốc độ + chất lượng
```

---

## 1. Temporal Filter cho News Retrieval

### Vấn đề

`context_builder.py` gọi `search_news(question, top_k=5)` nhưng **không truyền time filter**.

Qdrant store đã hỗ trợ `published_from_ts` / `published_to_ts` (line 169-180 trong `qdrant_store.py`), nhưng không ai gọi.

### Giải pháp

#### [MODIFY] `chatbot/context_builder.py`

- Extract `TimeRange` từ câu hỏi (đã có `extract_time_range()`)
- Truyền `published_from_ts` / `published_to_ts` vào `search_news()`

```python
from chatbot.time_range import extract_time_range

def build_context(question: str, intent: str) -> Dict[str, Any]:
    time_range = extract_time_range(question)
    
    # ...
    
    if intent in ("news_rag", "hybrid"):
        # Convert TimeRange → timestamp filters
        from_ts = int(time_range.start.timestamp()) if time_range.start else None
        to_ts = int(time_range.end.timestamp()) if time_range.end else None
        
        # Thêm market_scope filter khi hỏi domestic
        market_scope = _guess_market_scope(question)
        
        context["news"] = search_news(
            question,
            top_k=10,  # retrieve nhiều, filter sau
            published_from_ts=from_ts,
            published_to_ts=to_ts,
            market_scope=market_scope,
        )
```

#### Fallback khi không có news trong window

Nếu Qdrant trả 0 kết quả trong time window → mở rộng window hoặc ghi note "không tìm thấy tin trong giai đoạn này".

```python
if not context["news"]["articles"]:
    # Retry without time filter, nhưng đánh dấu
    context["news"] = search_news(question, top_k=5)
    context["news"]["note"] = "Không tìm thấy tin trong giai đoạn yêu cầu. Các tin dưới đây từ thời điểm khác."
```

---

## 2. Compact News Context

### Vấn đề

Hiện tại `search_news()` trả `document` = full display_text (có thể hàng nghìn ký tự/bài). Đưa 5+ bài full → Ollama timeout.

### Giải pháp

#### [NEW] `chatbot/context_compressor.py`

```python
def compact_news_context(
    articles: list[dict],
    top_n: int = 3,
    max_chars_per_article: int = 500,
) -> str:
    """Rút gọn retrieved articles thành evidence blocks cho LLM."""
    # Sort by relevance score (descending)
    sorted_articles = sorted(articles, key=lambda a: a.get("score", 0) or 0, reverse=True)
    top_articles = sorted_articles[:top_n]
    
    blocks = []
    for i, a in enumerate(top_articles, start=1):
        doc = a.get("document", "")
        short_doc = doc[:max_chars_per_article]
        if len(doc) > max_chars_per_article:
            short_doc = short_doc.rsplit(" ", 1)[0] + "..."
        
        blocks.append(
            f"[{i}] {a.get('title', 'N/A')}\n"
            f"Source: {a.get('source_name', '')}\n"
            f"Published: {a.get('published_at', '')}\n"
            f"Event type: {a.get('event_type', '')}\n"
            f"Impact: {a.get('impact_score', 0)}\n"
            f"Evidence:\n{short_doc}"
        )
    
    return "\n\n".join(blocks)
```

#### [MODIFY] `chatbot/prompts.py`

Thay vì `json.dumps(context)` full, build prompt có structure:

```python
def build_answer_messages(question, context, history=None):
    price_text = _format_price_context(context.get("price"))
    news_text = compact_news_context(
        context.get("news", {}).get("articles", []),
        top_n=3,
        max_chars_per_article=500,
    )
    
    context_str = f"PRICE DATA:\n{price_text}\n\nNEWS EVIDENCE:\n{news_text}"
    # ... build messages with context_str instead of json.dumps
```

### Config

```python
# core/config.py
RAG_CONTEXT_TOP_N = int(os.getenv("RAG_CONTEXT_TOP_N", "3"))
RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "500"))
```

---

## 3. Fallback Answer Readable

### Vấn đề

`orchestrator.py` line 40-48: fallback = `str(price)` + `str(news)` → dump raw Python dict/JSON.

### Giải pháp

#### [MODIFY] `chatbot/orchestrator.py` — `_fallback_answer()`

```python
def _fallback_answer(intent: str, context: dict, exc: Exception) -> str:
    parts = [f"Không gọi được LLM ({type(exc).__name__}). "
             f"Dữ liệu truy vấn được:\n"]
    
    price = context.get("price")
    if intent in ("price_sql", "hybrid") and price and price.get("ok"):
        latest = price.get("latest", {})
        parts.append(
            f"Diễn biến giá:\n"
            f"- {price.get('type_code', 'N/A')} {price.get('period_days', 7)} ngày gần đây "
            f"{price.get('trend', 'N/A')}"
            f" {abs(price.get('change', 0)):,.0f} "
            f"({price.get('change_pct', 0):+.2f}%).\n"
            f"- Giá mới nhất: mua {latest.get('buy_price', 0):,.0f}, "
            f"bán {latest.get('sell_price', 0):,.0f}.\n"
            f"- RSI14: {price.get('rsi14', 0):.1f} ({price.get('rsi_summary', 'N/A')})."
        )
    
    news = context.get("news")
    if intent in ("news_rag", "hybrid") and news and news.get("articles"):
        articles = news["articles"][:3]
        parts.append("\nTin tức tìm được:")
        for i, a in enumerate(articles, 1):
            parts.append(
                f"{i}. {a.get('title', 'N/A')} - {a.get('source_name', '')} - "
                f"{a.get('published_at', '')[:10]}"
            )
    
    if not price and not news:
        parts.append("Không có dữ liệu price hay news.")
    
    return "\n".join(parts)
```

---

## 4. Chuyển sang Ollama Cloud-Free Model

### Vấn đề

`qwen2.5:7b` local → chậm, dễ timeout khi context dài. Anh muốn chuyển sang model cloud free qua Ollama.

### Lựa chọn

| Model | Ưu điểm | Nhược điểm |
|---|---|---|
| `qwen2.5:3b` | Nhẹ hơn 7b, vẫn local | Chất lượng kém hơn |
| `gemma3:4b` | Google, tiếng Việt tốt | Cần RAM |
| `phi4-mini` | Microsoft, rất nhẹ | Tiếng Việt yếu |
| **Gemini Flash** (cloud free) | Nhanh, free tier generous, tiếng Việt xuất sắc | Cần API key + internet |

### Đề xuất

Giữ nguyên architecture hiện tại (factory pattern), chỉ đổi `.env`:

**Option A — Gemini Flash (đã có client):**
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your_key
```

**Option B — Ollama + model nhẹ hơn:**
```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
```

> Không cần sửa code, chỉ đổi `.env`.

---

## Tóm tắt files cần sửa

| # | File | Action | Mô tả |
|---|---|---|---|
| 1 | `chatbot/context_builder.py` | MODIFY | Thêm temporal filter + market_scope |
| 2 | `chatbot/context_compressor.py` | NEW | Compact articles → evidence blocks |
| 3 | `chatbot/prompts.py` | MODIFY | Dùng compressor thay json.dumps |
| 4 | `chatbot/orchestrator.py` | MODIFY | Fallback readable |
| 5 | `core/config.py` | MODIFY | Thêm RAG_CONTEXT_TOP_N, RAG_CONTEXT_MAX_CHARS |
| 6 | `.env` | MODIFY | Đổi LLM_MODEL nếu cần |

**Tổng: 1 file mới + 4 files modify + 1 config**

---

## Verification Plan

### Sau fix 1 (temporal filter):
```
Câu hỏi: "Giá vàng 7 ngày gần đây"
Expected: News results có published_at trong 7 ngày, không có bài từ 2005/2020
```

### Sau fix 2 (compact context):
```
Log prompt length < 3000 chars (thay vì 10000+)
Ollama không timeout
```

### Sau fix 3 (fallback):
```
Kill Ollama → hỏi chatbot
Expected: Response readable, có giá cụ thể, không dump JSON
```

### Sau fix 4 (model):
```
Đổi .env → restart → hỏi cùng câu
Expected: Response nhanh hơn, chất lượng tốt hơn
```
