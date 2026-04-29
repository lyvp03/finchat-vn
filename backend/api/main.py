import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, gold_news, gold_price, health

# ---------------------------------------------------------------
# Logging: bắt buộc setup trước khi import các module khác
# để [FLOW] logs xuất hiện trên terminal uvicorn
# ---------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-22s] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # override bất kỳ config nào uvicorn đã set
)
# Tắt noise từ các thư viện bên ngoài
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== FinChat VN API starting up ===")
    from core.config import settings
    logger.info(
        "LLM: provider=%s model=%s cloud=%s",
        settings.LLM_PROVIDER,
        settings.LLM_MODEL,
        "ollama.com" in settings.OLLAMA_BASE_URL,
    )
    logger.info("Vector store: %s", settings.VECTOR_STORE)
    yield
    logger.info("=== FinChat VN API shutting down ===")


app = FastAPI(title="FinChat VN API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(gold_price.router)
app.include_router(gold_news.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"name": "FinChat VN API", "status": "ok"}
