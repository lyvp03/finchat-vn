"""Factory: tạo LLM client dựa trên .env config."""
import logging

from core.config import settings
from core.llm.base import BaseLLMClient

logger = logging.getLogger("llm_factory")


def _require_env(value: str, name: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{name} is required for LLM configuration. Set it in .env or deployment env.")
    return value


def get_llm_client() -> BaseLLMClient:
    """Trả về LLM client theo LLM_PROVIDER trong config."""
    provider = _require_env(settings.LLM_PROVIDER, "LLM_PROVIDER").lower()
    model = _require_env(settings.LLM_MODEL, "LLM_MODEL")

    if provider == "ollama":
        from core.llm.ollama_client import OllamaClient
        base_url = _require_env(settings.OLLAMA_BASE_URL, "OLLAMA_BASE_URL")
        is_cloud = "ollama.com" in base_url
        logger.info(
            "Using Ollama provider: model=%s cloud=%s base_url=%s",
            model, is_cloud, base_url,
        )
        return OllamaClient(
            model=model,
            base_url=base_url,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OLLAMA_API_KEY or None,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

    if provider == "gemini":
        from core.llm.gemini_client import GeminiClient
        api_key = _require_env(settings.GOOGLE_API_KEY, "GOOGLE_API_KEY")
        logger.info("Using Gemini provider: model=%s", model)
        return GeminiClient(
            api_key=api_key,
            model=model,
            temperature=settings.LLM_TEMPERATURE,
        )

    if provider == "mimo":
        from core.llm.openai_client import OpenAIClient
        api_key = _require_env(settings.MIMO_API_KEY, "MIMO_API_KEY")
        base_url = _require_env(settings.MIMO_BASE_URL, "MIMO_BASE_URL")
        logger.info("Using Mimo provider (via OpenAIClient): model=%s", model)
        return OpenAIClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

    if provider == "gpt-mini":
        from core.llm.openai_client import OpenAIClient
        api_key = _require_env(settings.GPT_MINI_API_KEY, "GPT_MINI_API_KEY")
        base_url = _require_env(settings.GPT_MINI_BASE_URL, "GPT_MINI_BASE_URL")
        logger.info("Using GPT-Mini provider (via OpenAIClient): model=%s", model)
        return OpenAIClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
