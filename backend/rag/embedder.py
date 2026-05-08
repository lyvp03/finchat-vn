"""Embedding wrapper for gold news RAG — OpenAI-compatible API."""
import logging
from typing import Iterable, List

import httpx

from core.config import settings

logger = logging.getLogger("embedder")

_MAX_BATCH = 100  # OpenAI API limit per request


class OpenAIEmbedder:
    """Embedding via OpenAI-compatible API (text-embedding-3-small)."""

    def __init__(self, model_name: str | None = None):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_EMBEDDING_BASE_URL.rstrip("/")
        self.model = model_name or settings.EMBEDDING_MODEL
        self._dimension = 1536

        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. "
                "Set it in .env or environment variables."
            )

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Embed a list of texts via the /v1/embeddings endpoint.

        Automatically batches requests to stay within the 100-text API limit.
        """
        texts = list(texts)
        if not texts:
            return []

        all_vectors: List[List[float]] = []
        for start in range(0, len(texts), _MAX_BATCH):
            batch = texts[start : start + _MAX_BATCH]
            vectors = self._call_api(batch)
            all_vectors.extend(vectors)

        return all_vectors

    def dimension(self) -> int:
        return self._dimension

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Single API call for a batch of texts."""
        response = httpx.post(
            f"{self.base_url}/v1/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": texts,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        # Sort by index to preserve input order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in embeddings]


def article_to_embedding_text(article: dict) -> str:
    title = article.get("title") or ""
    summary = article.get("summary") or ""
    content = article.get("content") or ""
    return f"{title}. {summary}. {content[:500]}".strip()
