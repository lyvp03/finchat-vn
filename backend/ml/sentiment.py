"""
Sentiment analysis: FinBERT (EN) + Multilingual (VI) + Gold-specific adjustment.

score_sentiment() trả về float [-1.0, 1.0] từ góc nhìn giá vàng:
  - Dương = bullish cho vàng
  - Âm = bearish cho vàng
"""
import logging

logger = logging.getLogger("sentiment")

# ══════════════════════════════════════════════════════
# GOLD-SPECIFIC SENTIMENT RULES
# ══════════════════════════════════════════════════════

GOLD_BULLISH_SIGNALS = [
    "gold rises", "gold gains", "gold rallies", "gold surges", "gold climbs",
    "gold hits", "gold soars", "gold jumps",
    "vàng tăng", "giá vàng tăng", "vàng lên",
    "rate cut", "cắt giảm lãi suất", "dovish", "giảm lãi suất",
    "dollar weakens", "dollar falls", "dollar drops", "usd giảm",
    "inflation concern", "inflation rises", "lạm phát tăng",
    "safe haven demand", "safe-haven demand", "trú ẩn an toàn",
    "geopolitical risk", "war escalat", "conflict",
    "central bank buy", "ngân hàng trung ương mua",
    "treasury yield falls", "yields fall", "lợi suất giảm",
    "recession fear", "economic slowdown", "suy thoái",
]

GOLD_BEARISH_SIGNALS = [
    "gold falls", "gold slips", "gold drops", "gold declines", "gold tumbles",
    "gold retreats", "gold dips", "gold sinks",
    "vàng giảm", "giá vàng giảm", "vàng xuống",
    "rate hike", "tăng lãi suất", "hawkish",
    "dollar strengthens", "dollar rises", "dollar gains", "usd tăng",
    "inflation cools", "inflation eases", "lạm phát giảm",
    "risk-on", "risk appetite",
    "treasury yield rises", "yields rise", "lợi suất tăng",
]

# ══════════════════════════════════════════════════════
# MODEL LOADING (lazy — chỉ load khi gọi lần đầu)
# ══════════════════════════════════════════════════════

_finbert = None
_multilingual = None


def _load_finbert():
    global _finbert
    if _finbert is None:
        from transformers import pipeline
        logger.info("Loading FinBERT model...")
        _finbert = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,
            device=-1,
            truncation=True,
            max_length=512,
        )
        logger.info("FinBERT loaded.")
    return _finbert


def _load_multilingual():
    global _multilingual
    if _multilingual is None:
        from transformers import pipeline
        logger.info("Loading multilingual sentiment model...")
        _multilingual = pipeline(
            "text-classification",
            model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
            device=-1,
            truncation=True,
            max_length=512,
        )
        logger.info("Multilingual sentiment model loaded.")
    return _multilingual


# ══════════════════════════════════════════════════════
# SCORING
# ══════════════════════════════════════════════════════

def _finbert_score(text: str) -> float:
    """FinBERT returns positive/negative/neutral → convert to [-1, 1]."""
    output = _load_finbert()(text[:512])
    # top_k=None → [[{label, score}, ...]] per input
    result = output[0] if isinstance(output[0], list) else output
    scores = {r["label"].lower(): r["score"] for r in result}
    return scores.get("positive", 0) - scores.get("negative", 0)


def _multilingual_score(text: str) -> float:
    """XLM-RoBERTa returns LABEL_0 (neg) / LABEL_1 (neu) / LABEL_2 (pos)."""
    output = _load_multilingual()(text[:512])
    result = output[0] if isinstance(output, list) else output
    # Handle single dict result
    if isinstance(result, dict):
        label = result["label"].lower()
        confidence = float(result["score"])
    else:
        label = result[0]["label"].lower()
        confidence = float(result[0]["score"])

    if "positive" in label or label == "label_2":
        return confidence
    elif "negative" in label or label == "label_0":
        return -confidence
    return 0.0


def _adjust_for_gold(text: str, raw_score: float) -> float:
    """Điều chỉnh sentiment theo góc nhìn giá vàng."""
    text_lower = text.lower()
    has_bullish = any(kw in text_lower for kw in GOLD_BULLISH_SIGNALS)
    has_bearish = any(kw in text_lower for kw in GOLD_BEARISH_SIGNALS)

    if has_bullish and not has_bearish:
        # Tin bullish cho vàng nhưng model trả negative → đảo chiều
        return abs(raw_score) if raw_score < 0 else raw_score

    if has_bearish and not has_bullish:
        # Tin bearish cho vàng nhưng model trả positive → đảo chiều
        return -abs(raw_score) if raw_score > 0 else raw_score

    return raw_score


def score_sentiment(text: str, language: str = "en") -> float:
    """
    Sentiment score [-1.0, 1.0] từ góc nhìn giá vàng.

    Dương = bullish cho vàng, âm = bearish cho vàng.
    """
    if not text or len(text.strip()) < 10:
        return 0.0

    try:
        if language == "vi":
            raw = _multilingual_score(text)
        else:
            raw = _finbert_score(text)

        adjusted = _adjust_for_gold(text, raw)
        return round(max(min(adjusted, 1.0), -1.0), 4)

    except Exception as e:
        logger.warning(f"Sentiment scoring failed: {e}")
        return 0.0
