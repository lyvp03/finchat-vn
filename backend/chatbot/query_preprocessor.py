"""Synonym expansion cho router — chạy trước keyword match."""
from __future__ import annotations

from chatbot.time_range import normalize_text

# Key/value đều ở dạng không dấu (sau normalize_text)
SYNONYM_MAP = {
    "gia may": "gia bao nhieu",
    "bao nhiu": "bao nhieu",
    "vang the gioi": "xauusd the gioi vang",
    "gold": "vang xauusd",
    "vang mieng sjc": "sjc",
    "vang sjc": "sjc",
    "nguyen do": "nguyen nhan",
    "do dau ma": "nguyen nhan tai sao",
    "anh huong boi": "anh huong",
    "lien quan den": "lien quan",
    "dang o muc": "gia",
    "dang giao dich": "gia",
    "muc gia": "gia",
}


def expand_synonyms(normalized_text: str) -> str:
    """
    Expand synonyms trên text đã normalize (không dấu, lowercase).

    Dùng cho router để tăng coverage keyword match.
    """
    for phrase, expansion in SYNONYM_MAP.items():
        if phrase in normalized_text:
            normalized_text = normalized_text.replace(phrase, expansion)
    return normalized_text
