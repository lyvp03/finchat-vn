"""OpenAI-compatible LLM client (dùng requests thay vì thư viện openai để nhẹ hơn)."""
import logging
import time
from typing import Dict, List, Optional

import requests

from core.llm.base import BaseLLMClient

logger = logging.getLogger("openai_client")

_RETRYABLE_STATUS = {500, 502, 503, 504}
_MAX_RETRIES = 3
_RETRY_DELAY_SEC = 2.0


class OpenAIClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.1,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.timeout = timeout

        logger.info(
            "OpenAIClient initialized: model=%s base_url=%s",
            self.model, self.base_url,
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
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        if "gpt-5" in self.model.lower() or "o1" in self.model.lower():
            # Một số model o1 / gpt-5 qua litellm proxy không hỗ trợ gửi tham số temperature
            if "temperature" in payload:
                del payload["temperature"]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions") and not url.endswith("chat/completions"):
            if url.endswith("/v1"):
                url = f"{url}/chat/completions"
            else:
                url = f"{url}/v1/chat/completions"
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
                    response.raise_for_status()

                response.raise_for_status()
                break

            except requests.exceptions.Timeout:
                logger.error("[LLM TIMEOUT] attempt=%d/%d", attempt, _MAX_RETRIES)
                last_exc = requests.exceptions.Timeout()
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY_SEC * attempt)
                    continue
                raise last_exc

            except requests.exceptions.RequestException as exc:
                logger.error("[LLM HTTP ERROR] %s: body=%r", exc, getattr(exc.response, 'text', ''))
                raise

        elapsed = time.perf_counter() - t0
        data = response.json()
        
        # Standard OpenAI API returns choices[0].message.content
        if "choices" in data and len(data["choices"]) > 0:
            result = data["choices"][0]["message"]["content"]
        else:
            logger.error("Unexpected response format: %s", data)
            raise ValueError(f"Unexpected response from API: {data}")

        logger.info(
            "[LLM SUCCESS] model=%s total_latency=%.2fs output_chars=%d",
            self.model, elapsed, len(result),
        )
        return result
