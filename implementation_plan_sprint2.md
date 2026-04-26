# Sprint 2 — RAG & Chatbot (Chi tiết)

Kết hợp `.md` spec (kiến trúc LLM, router, MCP, vector search) với codebase hiện tại.

## Mapping: Spec → Codebase thực tế

| Spec path (`.md`) | Thực tế (codebase) |
|---|---|
| `app/core/llm/` | `backend/core/llm/` |
| `app/chatbot/` | `backend/chatbot/` |
| `app/tools/` | `backend/tools/` |
| `app/config/settings.py` | `backend/core/config.py` (đã có) |

---

## Phase 1 — LLM Abstraction Layer

Mục tiêu: Interface chung, Ollama client, factory. Dev test bằng `qwen2.5:7b` local.

### [NEW] `core/llm/__init__.py`

### [NEW] `core/llm/base.py`

```python
class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, messages, temperature=None, response_format=None) -> str: ...
```

### [NEW] `core/llm/ollama_client.py`

- POST `/api/chat` đến Ollama local
- Stream = False, timeout = 180s
- JSON format support

### [NEW] `core/llm/gemini_client.py`

- `google-generativeai` package
- Convert messages → prompt text
- JSON response_mime_type support

### [NEW] `core/llm/factory.py`

```python
def get_llm_client() -> BaseLLMClient:
    # Đọc LLM_PROVIDER từ .env → return OllamaClient hoặc GeminiClient
```

### [MODIFY] `core/config.py`

Thêm LLM + RAG config:
```python
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_TOP_K = 5
```

### [MODIFY] `.env`

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
LLM_TEMPERATURE=0.1
OLLAMA_BASE_URL=http://localhost:11434
```

### Verify Phase 1

```python
from core.llm.factory import get_llm_client
llm = get_llm_client()
print(llm.generate([{"role": "user", "content": "Xin chào"}]))
```

---

## Phase 2 — Vector DB (ChromaDB + Embedding)

Mục tiêu: Embed 224 bài RAG-eligible → ChromaDB → semantic search.

### [NEW] `rag/embedder.py`

- `sentence-transformers/all-MiniLM-L6-v2` (local, free, 384-dim)
- Embed text: `title + ". " + summary + ". " + content[:500]`
- Lazy load model (giống ml/sentiment.py pattern)

### [NEW] `rag/vector_store.py`

```python
class GoldNewsVectorStore:
    def __init__(self, persist_dir)
    def upsert_articles(articles)  # batch embed + upsert
    def search(query, top_k=5, market_scope=None, event_type=None) -> List[dict]
    def count() -> int
```

- ChromaDB collection: `gold_news`
- Metadata: `id, title, source_name, market_scope, event_type, sentiment_score, impact_score, published_at`

### [NEW] `rag/indexer.py`

Orchestrator: ClickHouse → filter RAG-eligible → embed → ChromaDB.

```python
def run_indexing():
    # Fetch from ClickHouse: is_relevant=1, quality>=0.50, len(content)>=200
    # Upsert to ChromaDB (idempotent by article id)
```

### [MODIFY] `jobs/worker/main.py`

Thêm `job_index_news()` chạy mỗi 2 giờ (sau enrichment).

### Verify Phase 2

```python
from rag.vector_store import GoldNewsVectorStore
store = GoldNewsVectorStore()
results = store.search("Fed giảm lãi suất", top_k=3)
# Expect: 3 bài liên quan đến Fed policy
```

---

## Phase 3 — Tools (MCP SQL + Vector Search)

Mục tiêu: Hai tool functions mà chatbot gọi để lấy data.

### [NEW] `tools/price_tool.py`

Thay MCP SQL tool. Gọi trực tiếp ClickHouse qua repository:

```python
def get_latest_price(type_code=None) -> dict:
    # GoldPriceRepository.get_latest_snapshot()
    # Format kèm TYPE_CODE_METADATA (tên, đơn vị)

def get_price_analysis(type_code="SJL1L10", days=7) -> dict:
    # get_historical_data() → tính trend, top moves, RSI summary
```

### [NEW] `tools/news_tool.py`

```python
def search_news(query, market_scope=None, top_k=5) -> dict:
    # GoldNewsVectorStore.search()
    # Return: title, summary, sentiment, impact, source, date

def get_news_summary(days=7) -> dict:
    # Aggregate: sentiment avg, top event_types, count by scope
```

### Verify Phase 3

```python
from tools.price_tool import get_latest_price, get_price_analysis
from tools.news_tool import search_news

print(get_latest_price("SJL1L10"))
print(get_price_analysis("XAUUSD", days=7))
print(search_news("Fed lãi suất"))
```

---

## Phase 4 — Chatbot Orchestrator

Mục tiêu: Router + context builder + prompts + orchestrator.

### [NEW] `chatbot/__init__.py`

### [NEW] `chatbot/router.py`

Rule-based intent detection (từ spec):

```python
def route_question(question: str) -> str:
    # "price_sql" | "news_rag" | "hybrid" | "general"
```

### [NEW] `chatbot/context_builder.py`

```python
def build_context(question, intent) -> dict:
    # intent=price_sql → gọi price_tool
    # intent=news_rag → gọi news_tool 
    # intent=hybrid → gọi cả hai
    # intent=general → context rỗng
```

### [NEW] `chatbot/prompts.py`

System prompt chống hallucination (từ spec):
```
- Chỉ trả lời dựa trên context
- Không tự bịa giá, ngày, nguồn
- Nếu thiếu data → nói rõ
- Trả lời tiếng Việt, ngắn gọn
```

### [NEW] `chatbot/orchestrator.py`

```python
def answer_question(question: str, history: list = None) -> dict:
    intent = route_question(question)
    context = build_context(question, intent)
    messages = build_answer_messages(question, context)
    llm = get_llm_client()
    answer = llm.generate(messages)
    return {"response": answer, "intent": intent, "sources": context}
```

### Verify Phase 4

```python
from chatbot.orchestrator import answer_question
result = answer_question("Giá vàng SJC hôm nay?")
# Expect: câu trả lời có giá cụ thể từ DB
```

---

## Phase 5 — FastAPI Endpoints

### [NEW] `api/main.py`

FastAPI app, CORS, mount routers.

### [NEW] `api/routes/gold_price.py`

```
GET /api/price/latest
GET /api/price/history?type=SJL1L10&days=30
```

### [NEW] `api/routes/gold_news.py`

```
GET /api/news/latest?limit=10&market_scope=domestic
GET /api/news/search?q=Fed&top_k=5
```

### [NEW] `api/routes/chat.py`

```
POST /api/chat
Body: {"message": "...", "history": []}
Response: {"response": "...", "intent": "...", "sources": {...}}
```

---

## Phase 6 — Test & Polish

### Test scenarios (từ spec):

| # | Question | Expected intent | Expected answer has |
|---|---|---|---|
| 1 | Giá vàng SJC hôm nay? | price_sql | Giá cụ thể |
| 2 | Tin nào ảnh hưởng đến vàng? | news_rag | News titles |
| 3 | Vì sao giá vàng tăng tuần này? | hybrid | Price + news |
| 4 | Giá bitcoin bao nhiêu? | general | Không biết / ngoài phạm vi |

### Anti-hallucination test:
- Hỏi giá mà không có context → phải nói "cần truy vấn DB"
- Không được bịa số liệu

---

## File tổng kết

| Phase | Files | Type |
|---|---|---|
| 1 | `core/llm/base.py`, `ollama_client.py`, `gemini_client.py`, `factory.py` | NEW |
| 1 | `core/config.py`, `.env` | MODIFY |
| 2 | `rag/embedder.py`, `rag/vector_store.py`, `rag/indexer.py` | NEW |
| 2 | `jobs/worker/main.py` | MODIFY |
| 3 | `tools/price_tool.py`, `tools/news_tool.py` | NEW |
| 4 | `chatbot/router.py`, `context_builder.py`, `prompts.py`, `orchestrator.py` | NEW |
| 5 | `api/main.py`, `api/routes/gold_price.py`, `gold_news.py`, `chat.py` | NEW |

**Tổng: 15 files mới + 3 files modify**

---

## Dependencies cần cài

```
pip install chromadb sentence-transformers google-generativeai
```

(`chromadb` + `sentence-transformers` cho RAG, `google-generativeai` cho Gemini fallback)

---

## Câu hỏi cho anh

> [!IMPORTANT]
> 1. Anh đã cài Ollama + model `qwen2.5:7b` rồi đúng không? Em cần verify trước khi implement.
> 2. Anh có `GOOGLE_API_KEY` chưa? Hay Sprint 2 chỉ dùng Ollama local?
> 3. Có cần MCP server riêng hay em gọi trực tiếp ClickHouse qua repository (đơn giản hơn)?
