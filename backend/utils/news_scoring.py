"""
News scoring functions: quality, relevance, impact, extraction (symbols/tags/entities).
No DB, no side-effects. Input/output only.
"""
from typing import List

from utils._news_keywords import (
    DIRECT_GOLD_KEYWORDS,
    MACRO_KEYWORDS,
    NOISE_KEYWORDS,
    DOMESTIC_KEYWORDS,
    SYMBOL_RULES,
    TAG_RULES,
    ENTITY_RULES,
    EVENT_BASE_IMPACT,
)
from utils._news_helpers import (
    _contains_any,
    _count_keywords,
    _extract_by_rules,
    _get_full_text_lower,
)


def compute_quality_score(article) -> float:
    """Chấm điểm chất lượng bài viết. Reuters RSS có thang điểm riêng (max 0.50)."""
    title = getattr(article, "title", "") or ""
    summary = getattr(article, "summary", "") or ""
    content = getattr(article, "content", "") or ""
    source_name = (getattr(article, "source_name", "") or "").lower()
    source_type = (getattr(article, "source_type", "") or "").lower()
    published_at = getattr(article, "published_at", None)
    content_len = len(content)
    title_lower = title.lower()

    # Reuters RSS: title-only articles
    if (source_type == "rss" or source_name == "reuters") and content_len < 200:
        score = 0.30
        if _contains_any(title_lower, DIRECT_GOLD_KEYWORDS):
            score += 0.10
        if _contains_any(title_lower, MACRO_KEYWORDS):
            score += 0.05
        if published_at:
            score += 0.05
        return round(min(score, 0.50), 4)

    # Full-content articles
    score = 0.0
    if title:
        score += 0.20
    if summary:
        score += 0.10
    if published_at:
        score += 0.10
    if title and content and title.strip() != content.strip():
        score += 0.10
    if source_name:
        score += 0.10

    if content_len >= 800:
        score += 0.40
    elif content_len >= 200:
        score += 0.25
    elif content_len >= 50:
        score += 0.10

    return round(min(max(score, 0.0), 1.0), 4)


def compute_relevance_score(article) -> float:
    """Chấm điểm mức liên quan đến vàng. Noise keywords bị penalty nặng."""
    title_lower = (getattr(article, "title", "") or "").lower()
    full_lower = _get_full_text_lower(article)

    if _contains_any(full_lower, NOISE_KEYWORDS):
        return 0.05

    score = 0.0

    if _contains_any(title_lower, DIRECT_GOLD_KEYWORDS):
        score += 0.60
    elif _contains_any(full_lower, DIRECT_GOLD_KEYWORDS):
        score += 0.30

    if _contains_any(full_lower, DOMESTIC_KEYWORDS):
        score += 0.15

    macro_title = _count_keywords(title_lower, MACRO_KEYWORDS)
    macro_full = _count_keywords(full_lower, MACRO_KEYWORDS)
    if macro_title > 0:
        score += min(0.25, macro_title * 0.08)
    if macro_full > 0:
        score += min(0.25, macro_full * 0.04)

    generic_noise = ["breaking international news", "global market headlines", "top energy headlines"]
    if _contains_any(title_lower, generic_noise):
        score = min(score, 0.15)

    return round(min(max(score, 0.0), 1.0), 4)


def extract_symbols(article) -> List[str]:
    """Extract market symbols (GOLD, XAUUSD, SJC, FED, etc.)."""
    full_lower = _get_full_text_lower(article)
    return _extract_by_rules(full_lower, SYMBOL_RULES)


def extract_tags(article, symbols: List[str] = None) -> List[str]:
    """Extract topic tags. Accepts pre-computed symbols to avoid redundant extraction."""
    full_lower = _get_full_text_lower(article)
    tags = set(_extract_by_rules(full_lower, TAG_RULES))

    # Fallback enrichment từ symbols
    if symbols is None:
        symbols = extract_symbols(article)
    sym_set = set(symbols)

    if "GOLD" in sym_set and getattr(article, "is_relevant", False):
        tags.add("gold_price")
    if sym_set & {"SJC", "DOJI", "PNJ", "BTMC", "VND"}:
        tags.add("domestic_gold")
    if "FED" in sym_set:
        tags.add("fed")
    if "USD" in sym_set:
        tags.add("usd")
    if "DXY" in sym_set:
        tags.add("dxy")
    if "US10Y" in sym_set:
        tags.add("bond_yield")
    if "CPI" in sym_set:
        tags.update(["cpi", "inflation"])
    if "PCE" in sym_set:
        tags.update(["pce", "inflation"])
    if "NFP" in sym_set:
        tags.add("nfp")
    if _contains_any(full_lower, ["spot gold", "gold futures", "comex gold", "vàng thế giới"]):
        tags.add("world_gold")

    return sorted(tags)


def extract_entities(article) -> List[str]:
    """Extract named entities (Fed, SJC, USD, Gold, Vietnam, etc.)."""
    full_lower = _get_full_text_lower(article)
    return _extract_by_rules(full_lower, ENTITY_RULES)


def compute_impact_score(article) -> float:
    """Mức ảnh hưởng đến giá vàng. Dựa trên event_type × relevance × quality."""
    event_type = getattr(article, "event_type", "other") or "other"
    relevance = float(getattr(article, "relevance_score", 0.0) or 0.0)
    quality = float(getattr(article, "quality_score", 0.0) or 0.0)
    is_relevant = bool(getattr(article, "is_relevant", False))

    impact = EVENT_BASE_IMPACT.get(event_type, 0.20)
    impact = impact * (0.6 + 0.4 * relevance)

    if quality < 0.35:
        impact *= 0.6
    elif quality < 0.50:
        impact *= 0.85

    if not is_relevant:
        impact = min(impact, 0.20)

    return round(min(max(impact, 0.0), 1.0), 4)
