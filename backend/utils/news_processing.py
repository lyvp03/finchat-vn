"""
Hàm thuần cho news preprocessing.
Không có DB, không side-effect. Input/output only.

Chuyển từ audit notebook (đã validate trên 698 bài).
"""
import re
import html
import hashlib
import unicodedata
from typing import List

# ══════════════════════════════════════════════════════
# KEYWORD DICTIONARIES
# ══════════════════════════════════════════════════════

DIRECT_GOLD_KEYWORDS = [
    # English
    "gold", "xauusd", "xau/usd", "bullion", "precious metal", "precious metals",
    "spot gold", "gold futures", "gold price", "gold prices", "comex gold",
    # Vietnamese
    "giá vàng", "vàng miếng", "vàng nhẫn", "vàng sjc", "sjc", "doji", "pnj",
    "bảo tín minh châu", "btmc", "vàng thế giới", "vàng trong nước", "kim loại quý",
]

MACRO_KEYWORDS = [
    # English
    "fed", "federal reserve", "fomc", "interest rate", "rate cut", "rate hike",
    "monetary policy", "hawkish", "dovish",
    "inflation", "cpi", "pce", "core pce", "nfp", "nonfarm payrolls", "jobs report",
    "unemployment", "recession", "economic slowdown", "gdp",
    "usd", "u.s. dollar", "us dollar", "dollar", "dxy",
    "treasury yield", "bond yield", "10-year yield", "real yield",
    "safe haven", "safe-haven", "geopolitical", "war", "conflict",
    "tariff", "trade war", "central bank",
    # Vietnamese
    "cục dự trữ liên bang", "lãi suất", "cắt giảm lãi suất", "tăng lãi suất",
    "chính sách tiền tệ", "lạm phát", "thất nghiệp", "suy thoái",
    "đồng usd", "đô la", "đồng bạc xanh",
    "lợi suất trái phiếu", "trái phiếu kho bạc",
    "trú ẩn an toàn", "tài sản trú ẩn", "địa chính trị",
    "chiến tranh", "xung đột", "thuế quan", "ngân hàng trung ương",
]

NOISE_KEYWORDS = [
    "gold card", "gold visa", "golden visa", "gold medal", "gold award",
    "golden globe", "goldman", "thẻ vàng", "huy chương vàng", "quả cầu vàng",
]

DOMESTIC_KEYWORDS = [
    "sjc", "doji", "pnj", "nhnn", "bảo tín", "btmc",
    "vàng miếng", "vàng nhẫn", "tỷ giá", "vàng trong nước",
]

INTL_KEYWORDS = [
    "xau", "xauusd", "fed", "cpi", "nfp", "dxy",
    "spot gold", "gold futures", "bullion", "treasury", "dollar",
]

SYMBOL_RULES = {
    "GOLD": ["gold", "giá vàng", "vàng", "bullion", "precious metal", "spot gold", "gold futures", "kim loại quý"],
    "XAUUSD": ["xauusd", "xau/usd", "spot gold"],
    "SJC": ["sjc", "vàng sjc", "vàng miếng"],
    "USD": ["usd", "u.s. dollar", "us dollar", "dollar", "đồng usd", "đô la", "đồng bạc xanh"],
    "DXY": ["dxy", "dollar index"],
    "US10Y": ["10-year yield", "treasury yield", "bond yield", "lợi suất trái phiếu", "trái phiếu kho bạc"],
    "FED": ["fed", "federal reserve", "fomc", "cục dự trữ liên bang"],
    "CPI": ["cpi", "consumer price index", "lạm phát"],
    "PCE": ["pce", "core pce"],
    "NFP": ["nfp", "nonfarm payrolls", "jobs report", "bảng lương phi nông nghiệp"],
    "VND": ["vnd", "việt nam", "trong nước"],
    "PNJ": ["pnj"],
    "DOJI": ["doji"],
    "BTMC": ["bảo tín minh châu", "btmc"],
}

TAG_RULES = {
    "gold_price": ["gold price", "gold prices", "giá vàng", "spot gold", "gold futures"],
    "domestic_gold": ["vàng trong nước", "vàng miếng", "vàng nhẫn", "sjc", "doji", "pnj", "btmc"],
    "world_gold": ["world gold", "global gold", "vàng thế giới", "spot gold", "comex gold"],
    "sjc": ["sjc", "vàng sjc", "vàng miếng"],
    "gold_ring": ["vàng nhẫn", "nhẫn trơn"],
    "fed": ["fed", "federal reserve", "fomc", "cục dự trữ liên bang"],
    "interest_rate": ["interest rate", "rate cut", "rate hike", "lãi suất", "cắt giảm lãi suất", "tăng lãi suất"],
    "usd": ["usd", "u.s. dollar", "us dollar", "dollar", "đồng usd", "đô la", "đồng bạc xanh"],
    "dxy": ["dxy", "dollar index"],
    "inflation": ["inflation", "lạm phát"],
    "cpi": ["cpi", "consumer price index"],
    "pce": ["pce", "core pce"],
    "nfp": ["nfp", "nonfarm payrolls", "jobs report"],
    "bond_yield": ["treasury yield", "bond yield", "10-year yield", "lợi suất trái phiếu"],
    "geopolitical": ["geopolitical", "war", "conflict", "địa chính trị", "chiến tranh", "xung đột"],
    "safe_haven": ["safe haven", "safe-haven", "trú ẩn an toàn", "tài sản trú ẩn"],
    "tariff": ["tariff", "trade war", "thuế quan", "chiến tranh thương mại"],
    "central_bank": ["central bank", "central banks", "ngân hàng trung ương"],
    "stock_market": ["stock market", "stocks", "equities", "chứng khoán", "cổ phiếu"],
    "oil": ["oil", "crude", "brent", "wti", "dầu"],
}

ENTITY_RULES = {
    "Fed": ["fed", "federal reserve", "fomc", "cục dự trữ liên bang"],
    "SJC": ["sjc", "vàng sjc"],
    "DOJI": ["doji"],
    "PNJ": ["pnj"],
    "Bao Tin Minh Chau": ["bảo tín minh châu", "btmc"],
    "USD": ["usd", "u.s. dollar", "us dollar", "dollar", "đồng usd", "đồng bạc xanh"],
    "DXY": ["dxy", "dollar index"],
    "CPI": ["cpi", "consumer price index"],
    "PCE": ["pce", "core pce"],
    "NFP": ["nfp", "nonfarm payrolls", "jobs report"],
    "Gold": ["gold", "giá vàng", "vàng", "bullion"],
    "Vietnam": ["việt nam", "vietnam", "trong nước"],
    "China": ["china", "trung quốc"],
    "Russia": ["russia", "nga"],
    "Ukraine": ["ukraine"],
    "Middle East": ["middle east", "trung đông"],
}

EVENT_TYPE_PRIORITY = [
    "domestic_market", "fed_policy", "inflation_data", "usd_movement",
    "bond_yield", "geopolitical_risk", "tariff_trade", "central_bank_demand",
    "economic_growth", "stock_market_risk", "gold_price_update",
]

EVENT_TYPE_RULES = {
    "domestic_market": ["vàng miếng", "vàng nhẫn", "vàng sjc", "vàng trong nước", "sjc", "doji", "pnj", "bảo tín minh châu", "btmc"],
    "fed_policy": ["fed", "federal reserve", "fomc", "interest rate", "rate cut", "rate hike", "monetary policy", "hawkish", "dovish", "cục dự trữ liên bang", "lãi suất", "cắt giảm lãi suất", "tăng lãi suất", "chính sách tiền tệ"],
    "inflation_data": ["inflation", "cpi", "pce", "core pce", "consumer price index", "lạm phát"],
    "usd_movement": ["usd", "u.s. dollar", "us dollar", "dollar", "dxy", "đồng usd", "đô la", "đồng bạc xanh"],
    "bond_yield": ["treasury yield", "bond yield", "10-year yield", "real yield", "lợi suất trái phiếu", "trái phiếu kho bạc"],
    "geopolitical_risk": ["geopolitical", "safe haven", "safe-haven", "war", "conflict", "middle east", "ukraine", "russia", "địa chính trị", "trú ẩn an toàn", "chiến tranh", "xung đột"],
    "tariff_trade": ["tariff", "trade war", "trade tension", "thuế quan", "chiến tranh thương mại"],
    "central_bank_demand": ["central bank buying", "central bank demand", "central banks", "ngân hàng trung ương mua vàng", "ngân hàng trung ương"],
    "economic_growth": ["gdp", "economic growth", "economic slowdown", "recession", "suy thoái", "tăng trưởng kinh tế"],
    "stock_market_risk": ["stock market", "stocks", "equities", "wall street", "s&p 500", "nasdaq", "chứng khoán", "cổ phiếu"],
    "gold_price_update": ["gold price", "gold prices", "spot gold", "gold futures", "bullion", "precious metals", "giá vàng", "vàng thế giới", "kim loại quý"],
}

EVENT_BASE_IMPACT = {
    "fed_policy": 0.85, "inflation_data": 0.85, "usd_movement": 0.80,
    "bond_yield": 0.80, "geopolitical_risk": 0.75, "central_bank_demand": 0.75,
    "tariff_trade": 0.65, "gold_price_update": 0.65, "domestic_market": 0.60,
    "stock_market_risk": 0.45, "economic_growth": 0.45, "other": 0.20,
}


# ══════════════════════════════════════════════════════
# CORE HELPERS
# ══════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════
# SCORING & CLASSIFICATION FUNCTIONS
#
# Tất cả nhận article đã clean (title/summary/content đã qua clean_text).
# Orchestrator clean 1 lần duy nhất trước khi gọi các hàm này.
# ══════════════════════════════════════════════════════

def _get_full_text_lower(article) -> str:
    """Build lowercased full text from article. Assumes fields already cleaned."""
    title = getattr(article, "title", "") or ""
    summary = getattr(article, "summary", "") or ""
    content = getattr(article, "content", "") or ""
    return f"{title} {summary} {content}".lower()


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


# ══════════════════════════════════════════════════════
# NEWS TIER CLASSIFICATION
# ══════════════════════════════════════════════════════

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
