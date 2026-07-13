import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Tải biến môi trường từ .env (cùng cấp với backend/)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()


def _env(name: str) -> str:
    """Read a string env var without baking provider/model defaults into code."""
    return os.getenv(name, "").strip()


class Settings:
    # ClickHouse Config
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "gold")
    CLICKHOUSE_SECURE = os.getenv("CLICKHOUSE_SECURE", "false").lower() in ("1", "true", "yes")

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
    # Provider/model are intentionally env-only so switching LLMs only requires .env changes.
    LLM_PROVIDER = _env("LLM_PROVIDER").lower()
    LLM_MODEL = _env("LLM_MODEL")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    OLLAMA_BASE_URL = _env("OLLAMA_BASE_URL")
    OLLAMA_API_KEY = _env("OLLAMA_API_KEY")
    GOOGLE_API_KEY = _env("GOOGLE_API_KEY")
    GOOGLE_API_KEYS: list[str] = [
        k.strip() for k in os.getenv("GOOGLE_API_KEYS", "").split(",") if k.strip()
    ]
    MIMO_API_KEY = _env("MIMO_API_KEY")
    MIMO_BASE_URL = _env("MIMO_BASE_URL")
    GPT_MINI_API_KEY = _env("GPT_MINI_API_KEY")
    GPT_MINI_BASE_URL = _env("GPT_MINI_BASE_URL")

    # --- OpenAI Embedding ---
    OPENAI_API_KEY = _env("OPENAI_API_KEY")
    OPENAI_EMBEDDING_BASE_URL = os.getenv(
        "OPENAI_EMBEDDING_BASE_URL",
        "https://aiportalapi.stu-platform.live/jpe"
    )

    # --- RAG / Vector DB ---
    VECTOR_STORE = os.getenv("VECTOR_STORE", "qdrant").lower()
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    QDRANT_URL = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "gold_news_chunks")
    QDRANT_TIMEOUT_SECONDS = int(os.getenv("QDRANT_TIMEOUT_SECONDS", "30"))
    QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "64"))
    QDRANT_TRUST_ENV = os.getenv("QDRANT_TRUST_ENV", "false").lower() in ("1", "true", "yes")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
    RAG_CANDIDATE_K = int(os.getenv("RAG_CANDIDATE_K", "30"))
    RAG_SHORT_ARTICLE_TOKENS = int(os.getenv("RAG_SHORT_ARTICLE_TOKENS", "600"))
    RAG_MAX_CHUNK_TOKENS = int(os.getenv("RAG_MAX_CHUNK_TOKENS", "400"))
    RAG_MIN_CHUNK_TOKENS = int(os.getenv("RAG_MIN_CHUNK_TOKENS", "80"))
    RAG_CHUNK_OVERLAP_PARAGRAPHS = int(os.getenv("RAG_CHUNK_OVERLAP_PARAGRAPHS", "1"))
    # Context compressor: bao nhiêu bài / chars đưa vào LLM
    RAG_CONTEXT_TOP_N = int(os.getenv("RAG_CONTEXT_TOP_N", "8"))
    RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "800"))

    # --- Context Management ---
    TOTAL_CONTEXT_BUDGET = int(os.getenv("TOTAL_CONTEXT_BUDGET", "8000"))
    MAX_PROMPT_TOKENS = int(os.getenv("MAX_PROMPT_TOKENS", "6000"))

settings = Settings()
