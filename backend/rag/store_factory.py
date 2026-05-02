"""Vector store factory."""
from __future__ import annotations

from core.config import settings


def get_news_vector_store():
    if settings.VECTOR_STORE == "qdrant":
        from rag.stores.qdrant_store import QdrantNewsVectorStore

        return QdrantNewsVectorStore()
    raise ValueError(f"Unsupported VECTOR_STORE={settings.VECTOR_STORE!r}. Only 'qdrant' is supported.")
