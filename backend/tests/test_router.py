import pytest

from chatbot.router import analyze_question, route_question


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Giá SJC hôm nay bao nhiêu?", "price_sql"),
        ("Trong 7 ngày gần đây, mã SJC tăng hay giảm?", "price_sql"),
        ("XAUUSD đang có xu hướng tăng hay giảm theo EMA20?", "price_sql"),
        ("Spread của DOJI trong 3 phiên gần nhất thế nào?", "price_sql"),
        ("Giá vàng SJC biến động gì so với tháng trước?", "price_sql"),
        ("Giá vàng hôm nay so với hôm qua ra sao?", "price_sql"),
        ("Có tin nào về Fed ảnh hưởng đến vàng không?", "news_rag"),
        ("Tóm tắt tin vàng gần đây từ Reuters.", "news_rag"),
        ("Có bài nào nói về ngân hàng trung ương mua vàng không?", "news_rag"),
        ("Vì sao giá SJC giảm trong 7 ngày gần đây?", "hybrid"),
        ("Giá vàng tăng có liên quan đến Fed không?", "hybrid"),
        ("Tin tức nào giải thích biến động giá vàng tuần này?", "hybrid"),
        ("XAUUSD giảm có phải do USD mạnh lên không?", "hybrid"),
        ("Bitcoin hôm nay thế nào?", "general"),
        ("Cổ phiếu ngân hàng có nên mua không?", "general"),
        ("RSI là gì?", "general"),
    ],
)
def test_route_question(question, expected):
    assert route_question(question) == expected


def test_analyze_question_returns_debug_signals():
    result = analyze_question("Trong 7 ngày gần đây, mã SJC tăng hay giảm?")

    assert result.intent == "price_sql"
    assert result.confidence >= 0.8
    assert result.signals["has_price_signal"] is True
    assert result.signals["has_cause_or_news_signal"] is False
