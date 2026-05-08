"""Embedding wrapper for gold news RAG — Gemini Embedding API."""
import logging
import time
from typing import Iterable, List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception,
    before_sleep_log,
)

import httpx

from core.config import settings

logger = logging.getLogger("embedder")

# Gemini Free Tier is very strict on rate limits (15 RPM).
# Keep batches small to reduce per-request payload and avoid 429s.
_MAX_BATCH = 15
_INTER_BATCH_SLEEP = 8.0   # seconds between consecutive batches
_PRE_REQUEST_SLEEP = 5.0   # seconds before each API call


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on HTTP 429 (rate limit). Other errors should fail fast."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    return False


class GeminiEmbedder:
    """Embedding via Google Gemini API (gemini-embedding-2)."""

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
        """Embed a list of texts via Gemini API with throttling."""
        texts = list(texts)
        if not texts:
            return []

        all_vectors: List[List[float]] = []
        total_batches = (len(texts) + _MAX_BATCH - 1) // _MAX_BATCH

        for batch_idx, start in enumerate(range(0, len(texts), _MAX_BATCH)):
            batch = texts[start : start + _MAX_BATCH]

            # Throttle between batches (skip sleep before first batch)
            if batch_idx > 0:
                logger.info(
                    "Sleeping %.1fs between batches (%d/%d) …",
                    _INTER_BATCH_SLEEP, batch_idx + 1, total_batches,
                )
                time.sleep(_INTER_BATCH_SLEEP)

            logger.info(
                "Embedding batch %d/%d  (%d texts) …",
                batch_idx + 1, total_batches, len(batch),
            )
            vectors = self._call_api(batch)
            all_vectors.extend(vectors)

        logger.info("Finished embedding %d texts in %d batches.", len(texts), total_batches)
        return all_vectors

    def dimension(self) -> int:
        return self._dimension

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_random_exponential(min=4, max=120),
        stop=stop_after_attempt(20),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Single API call for a batch of texts using Gemini."""
        # Pre-request sleep to stay within 15 RPM free-tier limit.
        time.sleep(_PRE_REQUEST_SLEEP)

        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]}
            }
            for t in texts
        ]

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:batchEmbedContents?key={self.api_key}"
        )
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
