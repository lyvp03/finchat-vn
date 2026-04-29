import os
from dotenv import load_dotenv

# Tải biến môi trường từ .env (cùng cấp với backend/)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

class Settings:
    # ClickHouse Config
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "gold")
    
    # Application Config
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # --- News Preprocessing Thresholds ---
    NEWS_RELEVANCE_THRESHOLD = 0.35
    NEWS_QUALITY_MIN_RAG = 0.50
    NEWS_QUALITY_MIN_ANALYSIS = 0.35
    NEWS_QUALITY_MAX_RSS_ONLY = 0.50
    NEWS_DUP_TITLE_SIMILARITY = 0.90
    RAG_MIN_CONTENT_LEN = 200

    # --- LLM ---
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Cần khi dùng Ollama Cloud (lấy tại https://ollama.com/settings/keys)
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

    # --- RAG / Vector DB ---
    VECTOR_STORE = os.getenv("VECTOR_STORE", "qdrant").lower()
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    QDRANT_URL = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "gold_news_chunks")
    QDRANT_TIMEOUT_SECONDS = int(os.getenv("QDRANT_TIMEOUT_SECONDS", "30"))
    QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "64"))
    QDRANT_TRUST_ENV = os.getenv("QDRANT_TRUST_ENV", "false").lower() in ("1", "true", "yes")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "8"))
    RAG_CANDIDATE_K = int(os.getenv("RAG_CANDIDATE_K", "24"))
    RAG_SHORT_ARTICLE_TOKENS = int(os.getenv("RAG_SHORT_ARTICLE_TOKENS", "450"))
    RAG_MAX_CHUNK_TOKENS = int(os.getenv("RAG_MAX_CHUNK_TOKENS", "320"))
    RAG_MIN_CHUNK_TOKENS = int(os.getenv("RAG_MIN_CHUNK_TOKENS", "80"))
    RAG_CHUNK_OVERLAP_PARAGRAPHS = int(os.getenv("RAG_CHUNK_OVERLAP_PARAGRAPHS", "1"))
    # Context compressor: bao nhiêu bài / chars đưa vào LLM
    RAG_CONTEXT_TOP_N = int(os.getenv("RAG_CONTEXT_TOP_N", "3"))
    RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "500"))

settings = Settings()
