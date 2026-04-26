"""Ollama LLM client — gọi model local qua REST API."""
import logging
import requests
from typing import Dict, List, Optional

from core.llm.base import BaseLLMClient

logger = logging.getLogger("ollama_client")


class OllamaClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature

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

        logger.debug("Calling Ollama model=%s", self.model)
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=180,
        )
        response.raise_for_status()

        data = response.json()
        return data["message"]["content"]
