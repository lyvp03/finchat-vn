"""
News classification functions: market scope, event type, news tier.
No DB, no side-effects. Input/output only.
"""
from typing import List

from utils._news_keywords import (
    DIRECT_GOLD_KEYWORDS,
    MACRO_KEYWORDS,
    DOMESTIC_KEYWORDS,
    INTL_KEYWORDS,
    EVENT_TYPE_PRIORITY,
    EVENT_TYPE_RULES,
)
from utils._news_helpers import _contains_any, _get_full_text_lower


def classify_market_scope(article) -> str:
    """Phân loại domestic/international/mixed."""
    full_lower = _get_full_text_lower(article)
    source_name = (getattr(article, "source_name", "") or "").lower()

    has_vn = _contains_any(full_lower, DOMESTIC_KEYWORDS)
    has_intl = _contains_any(full_lower, INTL_KEYWORDS)

    if not has_vn and not has_intl:
        return "domestic" if source_name in ["vnexpress", "cafef"] else "international"
    if has_vn and has_intl:
        return "mixed"
    return "domestic" if has_vn else "international"


def classify_event_type(article) -> str:
    """Classify event type. Uses tags/symbols first, then keyword fallback."""
    tags = set(getattr(article, "tags", []) or [])
    symbols = set(getattr(article, "symbols", []) or [])

    if symbols & {"SJC", "DOJI", "PNJ", "BTMC", "VND"}:
        return "domestic_market"
    if "fed" in tags or "interest_rate" in tags:
        return "fed_policy"
    if tags & {"cpi", "pce", "inflation"}:
        return "inflation_data"
    if "usd" in tags or "dxy" in tags:
        return "usd_movement"
    if "bond_yield" in tags:
        return "bond_yield"
    if "geopolitical" in tags or "safe_haven" in tags:
        return "geopolitical_risk"
    if "tariff" in tags:
        return "tariff_trade"
    if "central_bank" in tags:
        return "central_bank_demand"
    if "stock_market" in tags:
        return "stock_market_risk"
    if tags & {"gold_price", "world_gold"} or "GOLD" in symbols:
        return "gold_price_update"

    # Keyword fallback
    full_lower = _get_full_text_lower(article)
    for event_type in EVENT_TYPE_PRIORITY:
        if _contains_any(full_lower, EVENT_TYPE_RULES.get(event_type, [])):
            return event_type

    return "other"


# ──────────────────────────────────────────────────────
# NEWS TIER CLASSIFICATION
# ──────────────────────────────────────────────────────

# Keywords indicating a headline is DIRECTLY about gold price movement
_DIRECT_PRICE_VERBS_VI = [
    "tăng", "giảm", "lao dốc", "vọt", "tăng vọt", "giảm mạnh", "tăng mạnh",
    "biến động", "đạt đỉnh", "rớt", "đi ngang", "lên", "xuống",
    "chạm mốc", "vượt mốc", "phá đỉnh", "lập đỉnh",
]

_DIRECT_PRICE_VERBS_EN = [
    "rise", "rises", "rose", "fall", "falls", "fell", "drop", "drops",
    "surge", "surges", "surged", "plunge", "plunges", "spike", "spikes",
    "climb", "climbs", "slip", "slips", "slid", "tumble", "tumbles",
    "hit", "hits", "record", "soar", "soars", "rally", "rallies",
]

_GOLD_PRICE_PHRASES_VI = [
    "giá vàng", "vàng sjc", "vàng miếng", "vàng nhẫn", "giá sjc",
    "vàng trong nước", "vàng thế giới",
]

_GOLD_PRICE_PHRASES_EN = [
    "gold price", "gold prices", "spot gold", "gold futures",
    "xauusd", "xau/usd", "comex gold",
]


def classify_news_tier(article) -> str:
    """
    Classify news article into evidence tiers.

    Returns:
        'direct'     — headline directly about gold price change
        'contextual' — related to gold market / macro factors
        'weak'       — loosely related or opinion
    """
    title = (getattr(article, "title", "") or "").lower()
    summary = (getattr(article, "summary", "") or "").lower()
    combined = f"{title} {summary}"

    # --- DIRECT: title mentions gold + price movement ---
    has_gold_phrase = any(p in combined for p in _GOLD_PRICE_PHRASES_VI + _GOLD_PRICE_PHRASES_EN)
    has_price_verb = any(v in combined for v in _DIRECT_PRICE_VERBS_VI + _DIRECT_PRICE_VERBS_EN)

    if has_gold_phrase and has_price_verb:
        return "direct"

    # --- Also direct if event_type is price_movement and relevance is high ---
    event_type = getattr(article, "event_type", "")
    relevance = getattr(article, "relevance_score", 0)
    if event_type == "price_movement" and relevance >= 0.5:
        return "direct"

    # --- CONTEXTUAL: mentions gold keywords OR macro keywords ---
    has_gold_keyword = any(k in combined for k in DIRECT_GOLD_KEYWORDS)
    has_macro_keyword = any(k in combined for k in MACRO_KEYWORDS)

    if has_gold_keyword or has_macro_keyword:
        return "contextual"

    # --- WEAK: everything else ---
    return "weak"
