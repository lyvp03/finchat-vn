import pytest

from core.config import settings
from rag.store_factory import get_news_vector_store
from rag.vector_store import GoldNewsVectorStore


def test_store_factory_returns_chroma(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE", "chroma")

    store = get_news_vector_store()

    assert isinstance(store, GoldNewsVectorStore)


def test_store_factory_rejects_unknown_store(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE", "unknown")

    with pytest.raises(ValueError):
        get_news_vector_store()
