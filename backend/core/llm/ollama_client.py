"""Ollama LLM client — hỗ trợ local và Ollama Cloud."""
import logging
import time
from typing import Dict, List, Optional

import requests

from core.llm.base import BaseLLMClient

logger = logging.getLogger("ollama_client")

# HTTP status codes đáng retry (transient server errors)
_RETRYABLE_STATUS = {500, 502, 503, 504}
_MAX_RETRIES = 3
_RETRY_DELAY_SEC = 2.0  # tăng gấp đôi mỗi lần (exponential backoff)


class OllamaClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        api_key: Optional[str] = None,
        timeout: int = 180,
    ):
        self.model = model
        # Cloud endpoint: https://ollama.com — local: http://localhost:11434
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.api_key = api_key  # Cần khi dùng Ollama Cloud
        self.timeout = timeout
        self._is_cloud = "ollama.com" in self.base_url

        if self._is_cloud and not self.api_key:
            logger.warning(
                "OLLAMA_API_KEY not set but base_url points to Ollama Cloud (%s). "
                "Requests will likely be rejected. "
                "Get your key at https://ollama.com/settings/keys",
                self.base_url,
            )
        logger.info(
            "OllamaClient initialized: model=%s base_url=%s cloud=%s",
            self.model, self.base_url, self._is_cloud,
        )

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if response_format == "json":
            payload["format"] = "json"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/api/chat"
        prompt_preview = (messages[-1].get("content", "") if messages else "")[:80]
        masked_key = (self.api_key[:8] + "...") if self.api_key else "None"
        total_chars = sum(len(m.get("content", "")) for m in messages)
        logger.info(
            "[LLM REQUEST] url=%s model=%s temp=%s timeout=%ss key=%s",
            url, self.model, temperature or self.temperature, self.timeout, masked_key,
        )
        logger.info(
            "[LLM REQUEST] messages=%d total_chars=%d prompt_preview=%r",
            len(messages), total_chars, prompt_preview,
        )

        t0 = time.perf_counter()
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                elapsed_attempt = time.perf_counter() - t0
                logger.info(
                    "[LLM HTTP] attempt=%d/%d status=%s elapsed=%.2fs",
                    attempt, _MAX_RETRIES, response.status_code, elapsed_attempt,
                )

                # Retry nếu là transient server error
                if response.status_code in _RETRYABLE_STATUS:
                    body_preview = response.text[:200]
                    logger.warning(
                        "[LLM RETRY] attempt=%d/%d got %s — retrying in %.1fs. body=%r",
                        attempt, _MAX_RETRIES, response.status_code,
                        _RETRY_DELAY_SEC * attempt, body_preview,
                    )
                    if attempt < _MAX_RETRIES:
                        time.sleep(_RETRY_DELAY_SEC * attempt)
                        continue
                    # Hết lần retry → raise
                    response.raise_for_status()

                response.raise_for_status()
                break  # Thành công

            except requests.exceptions.Timeout:
                logger.error(
                    "[LLM TIMEOUT] attempt=%d/%d after %ss (model=%s). "
                    "Consider a smaller model or shorter context.",
                    attempt, _MAX_RETRIES, self.timeout, self.model,
                )
                last_exc = requests.exceptions.Timeout()
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY_SEC * attempt)
                    continue
                raise last_exc

            except requests.exceptions.ConnectionError as exc:
                logger.error(
                    "[LLM CONN ERROR] Cannot connect to %s: %s",
                    self.base_url, exc,
                )
                raise

            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "?"
                body = exc.response.text[:300] if exc.response is not None else ""
                if status == 400:
                    logger.error(
                        "[LLM 400 BAD REQUEST] Payload rejected by Ollama. body=%r",
                        body,
                    )
                elif status == 401:
                    logger.error(
                        "Ollama 401 Unauthorized. "
                        "Set OLLAMA_API_KEY from https://ollama.com/settings/keys"
                    )
                elif status == 403:
                    logger.error(
                        "Ollama 403 Forbidden. Model '%s' may require a paid plan. "
                        "Check https://ollama.com/pricing",
                        self.model,
                    )
                elif status == 404:
                    logger.error(
                        "Ollama 404. Model '%s' not available on cloud. "
                        "Run /api/tags to list available models.",
                        self.model,
                    )
                else:
                    logger.error("Ollama HTTP error %s: %s body=%r", status, exc, body)
                raise

        elapsed = time.perf_counter() - t0
        data = response.json()
        result = data["message"]["content"]

        logger.info(
            "[LLM SUCCESS] model=%s total_latency=%.2fs output_chars=%d",
            self.model, elapsed, len(result),
        )
        return result
