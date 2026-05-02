"""
Shared internal helpers for news processing.
"""
from typing import List


def _contains_any(text_lower: str, keywords: list) -> bool:
    """Check if text_lower contains any keyword. text_lower must already be lowercased."""
    return any(kw in text_lower for kw in keywords)


def _count_keywords(text_lower: str, keywords: list) -> int:
    """Count how many keywords appear in text_lower. text_lower must already be lowercased."""
    return sum(1 for kw in keywords if kw in text_lower)


def _extract_by_rules(text_lower: str, rules: dict) -> List[str]:
    """Extract labels from rules dict. text_lower must already be lowercased."""
    return sorted(label for label, keywords in rules.items()
                  if _contains_any(text_lower, keywords))


def _get_full_text_lower(article) -> str:
    """Build lowercased full text from article. Assumes fields already cleaned."""
    title = getattr(article, "title", "") or ""
    summary = getattr(article, "summary", "") or ""
    content = getattr(article, "content", "") or ""
    return f"{title} {summary} {content}".lower()
