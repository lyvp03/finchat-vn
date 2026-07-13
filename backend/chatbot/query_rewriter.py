"""Rewrite câu hỏi thành dạng phù hợp cho vector search (news retrieval).

Strategy:
  1. Primary: dùng LLM (configured provider) để rewrite — hiểu ngữ nghĩa linh hoạt.
  2. Fallback: rule-based regex nếu LLM fail — nhanh, không phụ thuộc API.
"""
from __future__ import annotations

import logging
import re

from chatbot.time_range import normalize_text

logger = logging.getLogger("query_rewriter")


# ---------------------------------------------------------------
# LLM-based rewrite (primary)
# ---------------------------------------------------------------

_REWRITE_PROMPT = """Bạn là công cụ chuyển đổi câu hỏi.

NHIỆM VỤ: Viết lại câu hỏi của người dùng thành dạng KHAI BÁO ngắn gọn, phù hợp để tìm kiếm tin tức về thị trường vàng.

QUY TẮC:
- Giữ nguyên tên thực thể (SJC, XAUUSD, Fed, DOJI...)
- Bỏ từ hỏi (tại sao, có không, bao nhiêu...)
- Chuyển thành dạng khai báo/keyword
- Giữ nguyên thời gian nếu có (tuần qua, hôm nay...)
- CHỈ trả về câu đã rewrite, KHÔNG giải thích

VÍ DỤ:
- "Tại sao giá vàng SJC giảm tuần qua?" → "nguyên nhân giá vàng SJC giảm tuần qua"
- "Giá vàng có tăng trong thời gian tới không?" → "xu hướng giá vàng tăng giảm sắp tới"
- "Có tin gì về Fed ảnh hưởng đến vàng?" → "tin tức Fed tác động giá vàng"
- "Chuyện gì đang xảy ra với vàng vậy?" → "diễn biến biến động giá vàng gần đây"
- "XAUUSD giảm do USD mạnh phải không?" → "XAUUSD giảm nguyên nhân USD tăng mạnh"

Câu hỏi: {question}"""


def _llm_rewrite(question: str) -> str | None:
    """Rewrite bằng LLM. Trả về None nếu fail."""
    try:
        from core.llm.factory import get_llm_client
        client = get_llm_client()
        messages = [
            {"role": "user", "content": _REWRITE_PROMPT.format(question=question)},
        ]
        result = client.generate(messages, temperature=0.0)
        if result and result.strip():
            rewritten = result.strip().strip('"').strip("'")
            # Sanity check: không quá dài, không quá ngắn
            if 5 < len(rewritten) < 300:
                return rewritten
            logger.warning("[REWRITE] LLM output invalid length: %d", len(rewritten))
    except Exception as e:
        logger.warning("[REWRITE] LLM rewrite failed: %s", e)
    return None


# ---------------------------------------------------------------
# Rule-based rewrite (fallback)
# ---------------------------------------------------------------

# Pattern: interrogative → declarative keywords (dạng không dấu)
_REWRITE_RULES = [
    # "tại sao X?" → "nguyên nhân X"
    (r"^(tai sao|vi sao|do dau|ly do gi)\s+(.+?)\??\s*$", r"nguyen nhan \2"),
    # "X có tăng không?" → "X xu hướng tăng giảm"
    (r"(.+?)\s+(co tang khong|co giam khong|se tang khong|se giam khong)\??\s*$",
     r"\1 xu huong tang giam"),
    # "tin tức về X" → "sự kiện X tác động vàng"
    (r"tin tuc (ve|lien quan den)\s+(.+)", r"su kien \2 tac dong gia vang"),
    # "ảnh hưởng gì đến vàng?" → "tác động vàng"
    (r"(.+?)\s+anh huong (gi )?(den|toi) vang\??\s*$", r"\1 tac dong gia vang"),
]

NOISE_WORDS = frozenset({
    "co", "khong", "the", "vay", "a", "nhi", "nhe", "day", "thoi",
    "cho", "toi", "minh", "biet", "hoi", "duoc", "chua", "roi",
    "nao", "gi", "ma", "la", "cai", "ay",
})


def _rule_based_rewrite(question: str) -> str:
    """Fallback: rewrite bằng regex pattern."""
    text = normalize_text(question)
    original = text

    for pattern, replacement in _REWRITE_RULES:
        new_text = re.sub(pattern, replacement, text)
        if new_text != text:
            text = new_text
            break

    tokens = text.split()
    tokens = [t for t in tokens if t not in NOISE_WORDS]
    text = " ".join(tokens).strip()

    return text if text else original


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def rewrite_for_retrieval(question: str) -> str:
    """
    Rewrite câu hỏi cho vector search.

    Strategy: LLM primary → rule-based fallback.
    """
    original_normalized = normalize_text(question)

    # Try LLM first
    llm_result = _llm_rewrite(question)
    if llm_result:
        logger.info("[REWRITE] LLM: '%s' → '%s'", question[:50], llm_result[:50])
        return llm_result

    # Fallback to rule-based
    rule_result = _rule_based_rewrite(question)
    if rule_result != original_normalized:
        logger.info("[REWRITE] Rule: '%s' → '%s'", original_normalized[:50], rule_result[:50])
        return rule_result

    # No rewrite needed
    return original_normalized
