"""Shared vector store protocol."""
from __future__ import annotations

from typing import Any, Optional, Protocol

from rag.chunker import NewsChunk


class NewsVectorStore(Protocol):
    def upsert_chunks(self, chunks: list[NewsChunk]) -> int:
        ...

    def search(
        self,
        query: str,
        top_k: int = 5,
        market_scope: Optional[str] = None,
        event_type: Optional[str] = None,
        published_from_ts: Optional[int] = None,
        published_to_ts: Optional[int] = None,
        source_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        ...

    def count(self) -> int:
        ...
