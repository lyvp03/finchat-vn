# Sprint 2 — RAG & Chatbot

## Phase 1 — LLM Abstraction
- `[ ]` `core/llm/base.py` — interface
- `[ ]` `core/llm/ollama_client.py` — Ollama client
- `[ ]` `core/llm/factory.py` — factory
- `[ ]` `core/config.py` — thêm LLM config
- `[ ]` `.env` — thêm LLM vars
- `[ ]` Verify Ollama qwen2.5:7b

## Phase 2 — Vector DB
- `[ ]` `rag/embedder.py` — embedding wrapper
- `[ ]` `rag/vector_store.py` — ChromaDB CRUD
- `[ ]` `rag/indexer.py` — ClickHouse → ChromaDB
- `[ ]` Chạy indexing 224 bài RAG-eligible
- `[ ]` Verify search

## Phase 3 — Tools
- `[ ]` `tools/price_tool.py` — query price data
- `[ ]` `tools/news_tool.py` — vector search wrapper

## Phase 4 — Chatbot
- `[ ]` `chatbot/router.py` — intent routing
- `[ ]` `chatbot/context_builder.py` — gọi tools
- `[ ]` `chatbot/prompts.py` — system prompt
- `[ ]` `chatbot/orchestrator.py` — main flow

## Phase 5 — FastAPI
- `[ ]` `api/main.py` — app
- `[ ]` `api/routes/gold_price.py`
- `[ ]` `api/routes/gold_news.py`
- `[ ]` `api/routes/chat.py`

## Phase 6 — Test
- `[ ]` Test 4 scenarios
- `[ ]` Anti-hallucination test
