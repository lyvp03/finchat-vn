"""Input validation — chặn prompt injection + input quá dài."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("input_guardrail")

MAX_INPUT_LENGTH = 500

INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"you\s+are\s+now",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(a\s+)?(different|new)",
    r"jailbreak",
    r"DAN\s+mode",
    r"system\s*prompt",
    r"disregard\s+(previous|all)",
    r"new\s+instructions?\s*:",
    # Vietnamese patterns
    r"bo\s+qua.*?(context|huong\s+dan|thong\s+tin.*?cung\s+cap)",
    r"(chi\s+dung|su\s+dung)\s+thong\s+tin\s+sau",
    r"khong\s+(su\s+dung|can)\s+(context|thong\s+tin)",
    r"hay\s+gia\s+vo",
    r"lam\s+nhu\s+ban\s+la",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


@dataclass(frozen=True)
class InputCheck:
    is_safe: bool
    reason: str  # "ok", "empty_input", "input_too_long", "prompt_injection"


def check_input(question: str) -> InputCheck:
    """
    Validate user input trước khi vào pipeline.

    Returns InputCheck(is_safe=False, reason=...) nếu bị chặn.
    """
    if not question or not question.strip():
        return InputCheck(False, "empty_input")

    if len(question) > MAX_INPUT_LENGTH:
        logger.warning(
            "[INPUT GUARDRAIL] Input too long: %d chars (max %d)",
            len(question), MAX_INPUT_LENGTH,
        )
        return InputCheck(False, "input_too_long")

    import unicodedata
    # Bỏ dấu tiếng Việt để regex khớp cả chữ có dấu và không dấu
    normalized_q = re.sub(r'[đĐ]', 'd', question)
    normalized_q = unicodedata.normalize('NFKD', normalized_q).encode('ASCII', 'ignore').decode('utf-8')

    for pattern in _COMPILED:
        if pattern.search(normalized_q) or pattern.search(question):
            logger.warning(
                "[INPUT GUARDRAIL] Injection detected: %r",
                question[:100],
            )
            return InputCheck(False, "prompt_injection")

    return InputCheck(True, "ok")
