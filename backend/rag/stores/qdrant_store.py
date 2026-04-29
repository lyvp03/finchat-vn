"""Qdrant Cloud vector store for gold news chunks."""
from __future__ import annotations

import logging
from typing import Any, Optional

from core.config import settings
from rag.chunker import NewsChunk
from rag.embedder import SentenceTransformerEmbedder

logger = logging.getLogger("qdrant_store")


class QdrantNewsVectorStore:
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        embedder: SentenceTransformerEmbedder | None = None,
    ):
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.embedder = embedder or SentenceTransformerEmbedder()
        self._client = None

        if not self.url:
            raise RuntimeError("QDRANT_URL is not configured.")
        if not self.api_key:
            raise RuntimeError("QDRANT_API_KEY is not configured.")

    @property
    def client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError as exc:
                raise RuntimeError("qdrant-client is not installed. Install backend requirements first.") from exc
            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=settings.QDRANT_TIMEOUT_SECONDS,
                trust_env=settings.QDRANT_TRUST_ENV,
                check_compatibility=False,
            )
        return self._client

    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        try:
            info = self.client.get_collection(self.collection_name)
            existing_size = info.config.params.vectors.size
            expected_size = self.embedder.dimension()
            if existing_size != expected_size:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection_name}' vector size {existing_size} "
                    f"does not match embedding size {expected_size}."
                )
        except Exception as exc:
            if not _is_not_found_error(exc):
                raise
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedder.dimension(),
                    distance=Distance.COSINE,
                ),
            )

        self._ensure_payload_indexes()

    def upsert_chunks(self, chunks: list[NewsChunk]) -> int:
        if not chunks:
            return 0

        self.ensure_collection()
        total = 0
        batch_size = max(1, int(settings.QDRANT_UPSERT_BATCH_SIZE))
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            texts = [chunk.embed_text for chunk in batch]
            embeddings = self.embedder.embed(texts)
            points = [self._point_struct(chunk, vector) for chunk, vector in zip(batch, embeddings)]
            self.client.upsert(collection_name=self.collection_name, points=points)
            total += len(points)
        return total

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
        self.ensure_collection()
        query_vector = self.embedder.embed([query])[0]
        query_filter = self._filter(
            market_scope=market_scope,
            event_type=event_type,
            published_from_ts=published_from_ts,
            published_to_ts=published_to_ts,
            source_name=source_name,
        )
        results = self._search_points(query_vector=query_vector, query_filter=query_filter, top_k=top_k)
        return [self._row_from_point(point) for point in results]

    def count(self) -> int:
        self.ensure_collection()
        result = self.client.count(collection_name=self.collection_name, exact=True)
        return int(result.count)

    def _ensure_payload_indexes(self) -> None:
        from qdrant_client.models import PayloadSchemaType

        indexes = {
            "is_relevant": PayloadSchemaType.BOOL,
            "market_scope": PayloadSchemaType.KEYWORD,
            "event_type": PayloadSchemaType.KEYWORD,
            "source_name": PayloadSchemaType.KEYWORD,
            "language": PayloadSchemaType.KEYWORD,
            "symbols": PayloadSchemaType.KEYWORD,
            "tags": PayloadSchemaType.KEYWORD,
            "published_at_ts": PayloadSchemaType.INTEGER,
            "quality_score": PayloadSchemaType.FLOAT,
            "relevance_score": PayloadSchemaType.FLOAT,
        }
        for field_name, schema in indexes.items():
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=schema,
                )
            except Exception as exc:
                logger.debug("Skipping payload index %s: %s", field_name, exc)

    def _point_struct(self, chunk: NewsChunk, vector: list[float]):
        from qdrant_client.models import PointStruct

        payload = dict(chunk.metadata)
        payload["text"] = chunk.display_text
        return PointStruct(id=chunk.point_id, vector=vector, payload=payload)

    def _filter(
        self,
        market_scope: Optional[str],
        event_type: Optional[str],
        published_from_ts: Optional[int],
        published_to_ts: Optional[int],
        source_name: Optional[str],
    ):
        from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

        must = [
            FieldCondition(key="is_relevant", match=MatchValue(value=True)),
            FieldCondition(key="quality_score", range=Range(gte=float(settings.NEWS_QUALITY_MIN_RAG))),
        ]
        if market_scope:
            must.append(FieldCondition(key="market_scope", match=MatchValue(value=market_scope)))
        if event_type:
            must.append(FieldCondition(key="event_type", match=MatchValue(value=event_type)))
        if source_name:
            must.append(FieldCondition(key="source_name", match=MatchValue(value=source_name)))
        if published_from_ts is not None or published_to_ts is not None:
            range_kwargs = {}
            if published_from_ts is not None:
                range_kwargs["gte"] = published_from_ts
            if published_to_ts is not None:
                range_kwargs["lte"] = published_to_ts
            must.append(
                FieldCondition(
                    key="published_at_ts",
                    range=Range(**range_kwargs),
                )
            )
        return Filter(must=must)

    def _search_points(self, query_vector: list[float], query_filter, top_k: int):
        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )

        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        return result.points

    @staticmethod
    def _row_from_point(point) -> dict[str, Any]:
        payload = point.payload or {}
        return {
            "id": payload.get("doc_id") or payload.get("chunk_id") or str(point.id),
            "doc_id": payload.get("doc_id", ""),
            "chunk_id": payload.get("chunk_id", ""),
            "chunk_index": payload.get("chunk_index", 0),
            "title": payload.get("title", ""),
            "source_name": payload.get("source_name", ""),
            "market_scope": payload.get("market_scope", ""),
            "event_type": payload.get("event_type", ""),
            "sentiment_score": payload.get("sentiment_score", 0.0),
            "impact_score": payload.get("impact_score", 0.0),
            "published_at": payload.get("published_at", ""),
            "url": payload.get("url", ""),
            "document": payload.get("text") or payload.get("content_chunk", ""),
            "score": getattr(point, "score", None),
        }


def _is_not_found_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "not found" in text or "doesn't exist" in text or "404" in text
