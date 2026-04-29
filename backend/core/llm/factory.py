"""Factory: tạo LLM client dựa trên .env config."""
import logging

from core.config import settings
from core.llm.base import BaseLLMClient

logger = logging.getLogger("llm_factory")


def get_llm_client() -> BaseLLMClient:
    """Trả về LLM client theo LLM_PROVIDER trong config."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        from core.llm.ollama_client import OllamaClient
        is_cloud = "ollama.com" in settings.OLLAMA_BASE_URL
        logger.info(
            "Using Ollama provider: model=%s cloud=%s base_url=%s",
            settings.LLM_MODEL, is_cloud, settings.OLLAMA_BASE_URL,
        )
        return OllamaClient(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OLLAMA_API_KEY or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

    if provider == "gemini":
        from core.llm.gemini_client import GeminiClient
        logger.info("Using Gemini provider: model=%s", settings.LLM_MODEL)
        return GeminiClient(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
