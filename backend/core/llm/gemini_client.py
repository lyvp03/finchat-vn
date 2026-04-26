"""Gemini LLM client."""
from typing import Dict, List, Optional

from core.llm.base import BaseLLMClient


class GeminiClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.1,
    ):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini provider")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
    ) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Install backend requirements first."
            ) from exc

        genai.configure(api_key=self.api_key)
        generation_config = {
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if response_format == "json":
            generation_config["response_mime_type"] = "application/json"

        prompt = self._messages_to_prompt(messages)
        model = genai.GenerativeModel(self.model, generation_config=generation_config)
        response = model.generate_content(prompt)
        return response.text or ""

    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        lines = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            lines.append(f"{role.upper()}: {content}")
        return "\n\n".join(lines)
