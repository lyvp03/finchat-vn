"""Embedding wrapper for gold news RAG — OpenAI-compatible API."""
import logging
from typing import Iterable, List

import httpx

from core.config import settings

logger = logging.getLogger("embedder")

_MAX_BATCH = 100  # OpenAI API limit per request


class GeminiEmbedder:
    """Embedding via Google Gemini API (text-embedding-004)."""

    def __init__(self, model_name: str | None = None):
        self.api_key = settings.GOOGLE_API_KEY
        self.model = model_name or "gemini-embedding-2"
        self._dimension = 3072

        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not configured. "
                "Set it in .env or environment variables."
            )

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Embed a list of texts via Gemini API."""
        texts = list(texts)
        if not texts:
            return []

        all_vectors: List[List[float]] = []
        # Gemini batchEmbedContents max requests is 100
        for start in range(0, len(texts), _MAX_BATCH):
            batch = texts[start : start + _MAX_BATCH]
            vectors = self._call_api(batch)
            all_vectors.extend(vectors)

        return all_vectors

    def dimension(self) -> int:
        return self._dimension

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Single API call for a batch of texts using Gemini."""
        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]}
            }
            for t in texts
        ]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        response = httpx.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"requests": requests},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        return [item["values"] for item in data.get("embeddings", [])]


def article_to_embedding_text(article: dict) -> str:
    title = article.get("title") or ""
    summary = article.get("summary") or ""
    content = article.get("content") or ""
    return f"{title}. {summary}. {content[:500]}".strip()
