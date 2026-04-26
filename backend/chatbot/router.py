"""Rule-based intent router for gold finance questions."""

PRICE_KEYWORDS = ("giá", "bao nhiêu", "hôm nay", "mua vào", "bán ra", "sjc", "xauusd", "doji", "btmc")
NEWS_KEYWORDS = ("tin", "vì sao", "tại sao", "ảnh hưởng", "fed", "lãi suất", "cpi", "usd", "địa chính trị", "phân tích")
HYBRID_KEYWORDS = ("tăng", "giảm", "tuần này", "xu hướng", "biến động", "nguyên nhân")
OUT_OF_SCOPE_KEYWORDS = ("bitcoin", "btc", "ethereum", "cổ phiếu", "chứng khoán")


def route_question(question: str) -> str:
    text = question.lower()
    if any(keyword in text for keyword in OUT_OF_SCOPE_KEYWORDS):
        return "general"

    has_price = any(keyword in text for keyword in PRICE_KEYWORDS)
    has_news = any(keyword in text for keyword in NEWS_KEYWORDS)
    has_hybrid = any(keyword in text for keyword in HYBRID_KEYWORDS)

    if has_price and (has_news or has_hybrid):
        return "hybrid"
    if has_news and has_hybrid:
        return "hybrid"
    if has_price:
        return "price_sql"
    if has_news:
        return "news_rag"
    return "general"
