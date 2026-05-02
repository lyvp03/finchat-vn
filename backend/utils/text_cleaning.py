"""
Text cleaning utilities for news content.
No DB, no side-effects. Input/output only.
"""
import re
import html
import hashlib
import unicodedata


def clean_text(text) -> str:
    """Clean raw text: normalize unicode, unescape HTML, remove tags, collapse whitespace."""
    if text is None or (isinstance(text, float) and text != text):  # NaN check
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ").replace("\u200b", " ")
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sha256_hash(text: str) -> str:
    """SHA256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
