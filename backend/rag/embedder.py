"""Embedding wrapper for gold news RAG — Gemini Embedding API."""
import itertools
import logging
import threading
import time
from typing import Iterable, List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception,
    before_sleep_log,
)

import httpx

from core.config import settings

logger = logging.getLogger("embedder")

# Gemini Free Tier: 15 RPM per key, 1500 RPD per key.
# With 6 keys: effective 90 RPM / 9000 RPD.
_MAX_BATCH = 100  # batchEmbedContents supports up to 100
_INTER_BATCH_SLEEP = 2.0   # seconds between consecutive batches
_PRE_REQUEST_SLEEP = 1.0   # seconds before each API call


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on HTTP 429 (rate limit). Other errors should fail fast."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    return False


class _KeyRotator:
    """Thread-safe round-robin API key rotator."""

    def __init__(self, keys: list[str]):
        if not keys:
            raise RuntimeError(
                "No Google API keys configured. "
                "Set GOOGLE_API_KEYS (comma-separated) or GOOGLE_API_KEY in .env."
            )
        self._cycle = itertools.cycle(keys)
        self._lock = threading.Lock()
        self._count = len(keys)

    def next(self) -> str:
        with self._lock:
            return next(self._cycle)

    def __len__(self) -> int:
        return self._count


class GeminiEmbedder:
    """Embedding via Google Gemini API (gemini-embedding-2) with key rotation."""

    def __init__(self, model_name: str | None = None):
        # Build key pool: prefer GOOGLE_API_KEYS, fall back to single GOOGLE_API_KEY
        keys = settings.GOOGLE_API_KEYS or (
            [settings.GOOGLE_API_KEY] if settings.GOOGLE_API_KEY else []
        )
        self._keys = _KeyRotator(keys)
        self.model = model_name or "gemini-embedding-2"
        self._dimension = 3072

        logger.info(
            "GeminiEmbedder initialised with %d API key(s), model=%s",
            len(self._keys), self.model,
        )

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Embed a list of texts via Gemini API with throttling & key rotation."""
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
        wait=wait_fixed(60),
        stop=stop_after_attempt(30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Single API call for a batch of texts using Gemini (rotates keys)."""
        time.sleep(_PRE_REQUEST_SLEEP)

        api_key = self._keys.next()
        masked = f"{api_key[:6]}…{api_key[-4:]}" if len(api_key) > 10 else "***"

        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]}
            }
            for t in texts
        ]

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:batchEmbedContents?key={api_key}"
        )
        logger.debug("POST batchEmbedContents (%d texts) key=%s", len(texts), masked)
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
