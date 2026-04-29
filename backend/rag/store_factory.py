"""Vector store factory."""
from __future__ import annotations

from core.config import settings
from rag.vector_store import GoldNewsVectorStore


def get_news_vector_store():
    if settings.VECTOR_STORE == "qdrant":
        from rag.stores.qdrant_store import QdrantNewsVectorStore

        return QdrantNewsVectorStore()
    if settings.VECTOR_STORE == "chroma":
        return GoldNewsVectorStore()
    raise ValueError(f"Unsupported VECTOR_STORE={settings.VECTOR_STORE!r}")
