"""Interface chung cho mọi LLM provider."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """Gửi messages và nhận response text."""
        pass
