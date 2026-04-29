"""ChromaDB-backed vector store for enriched gold news."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.config import settings
from rag.chunker import NewsChunk, chunk_article
from rag.embedder import SentenceTransformerEmbedder, article_to_embedding_text


class GoldNewsVectorStore:
    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str = "gold_news",
        embedder: SentenceTransformerEmbedder | None = None,
    ):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name
        self.embedder = embedder or SentenceTransformerEmbedder()
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            try:
                import chromadb
            except ImportError as exc:
                raise RuntimeError("chromadb is not installed. Install backend requirements first.") from exc
            client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def upsert_articles(self, articles: List[Dict[str, Any]]) -> int:
        eligible = [article for article in articles if article.get("id")]
        if not eligible:
            return 0

        documents = [article_to_embedding_text(article) for article in eligible]
        embeddings = self.embedder.embed(documents)
        ids = [str(article["id"]) for article in eligible]
        metadatas = [self._metadata(article) for article in eligible]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(eligible)

    def upsert_chunks(self, chunks: List[NewsChunk]) -> int:
        eligible = [chunk for chunk in chunks if chunk.chunk_id]
        if not eligible:
            return 0

        documents = [chunk.display_text for chunk in eligible]
        embeddings = self.embedder.embed([chunk.embed_text for chunk in eligible])
        ids = [chunk.chunk_id for chunk in eligible]
        metadatas = [self._chunk_metadata(chunk) for chunk in eligible]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(eligible)

    def upsert_chunked_articles(self, articles: List[Dict[str, Any]]) -> int:
        chunks = []
        for article in articles:
            chunks.extend(chunk_article(article))
        return self.upsert_chunks(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        market_scope: Optional[str] = None,
        event_type: Optional[str] = None,
        published_from_ts: Optional[int] = None,
        published_to_ts: Optional[int] = None,
        source_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        where = {}
        if market_scope:
            where["market_scope"] = market_scope
        if event_type:
            where["event_type"] = event_type
        if source_name:
            where["source_name"] = source_name

        embeddings = self.embedder.embed([query])
        result = self.collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )

        rows = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for idx, article_id in enumerate(ids):
            metadata = metadatas[idx] or {}
            rows.append({
                "id": article_id,
                "doc_id": metadata.get("doc_id", metadata.get("id", "")),
                "chunk_id": metadata.get("chunk_id", article_id),
                "chunk_index": metadata.get("chunk_index", 0),
                "title": metadata.get("title", ""),
                "source_name": metadata.get("source_name", ""),
                "market_scope": metadata.get("market_scope", ""),
                "event_type": metadata.get("event_type", ""),
                "sentiment_score": metadata.get("sentiment_score", 0.0),
                "impact_score": metadata.get("impact_score", 0.0),
                "published_at": metadata.get("published_at", ""),
                "url": metadata.get("url", ""),
                "document": documents[idx] if idx < len(documents) else "",
                "distance": distances[idx] if idx < len(distances) else None,
            })
        return rows

    def count(self) -> int:
        return self.collection.count()

    @staticmethod
    def _metadata(article: Dict[str, Any]) -> Dict[str, Any]:
        published_at = article.get("published_at")
        return {
            "id": str(article.get("id", "")),
            "title": str(article.get("title", "")),
            "source_name": str(article.get("source_name", "")),
            "market_scope": str(article.get("market_scope", "")),
            "event_type": str(article.get("event_type", "")),
            "sentiment_score": float(article.get("sentiment_score") or 0),
            "impact_score": float(article.get("impact_score") or 0),
            "published_at": published_at.isoformat() if hasattr(published_at, "isoformat") else str(published_at or ""),
        }

    @staticmethod
    def _chunk_metadata(chunk: NewsChunk) -> Dict[str, Any]:
        metadata = dict(chunk.metadata)
        for key in ("symbols", "tags"):
            if key in metadata:
                metadata[key] = ",".join(str(item) for item in metadata.get(key) or [])
        if metadata.get("published_at_ts") is None:
            metadata["published_at_ts"] = 0
        return metadata
