"""
Quick local test — verify the new LLM-based news analyzer works.

Usage:
    cd backend
    python -m tests.test_news_analyzer
"""
import logging
import sys
from pathlib import Path

# Ensure backend/ is on sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test_analyzer")


# ── Test cases: title, content, language, expected hints ────────────────────

TEST_ARTICLES = [
    {
        "title": "Giá vàng SJC hôm nay tăng vọt lên 92 triệu đồng/lượng",
        "content": "Sáng nay 8/5, giá vàng SJC tại các cửa hàng lớn tại TP.HCM được niêm yết ở mức 91,5 - 92 triệu đồng/lượng, tăng 500 nghìn đồng so với hôm qua.",
        "source_name": "vnexpress",
        "language": "vi",
        "expect": "direct tier, domestic_market event, high relevance",
    },
    {
        "title": "Fed holds interest rates steady, signals no rush to cut",
        "content": "The Federal Reserve left its benchmark rate unchanged at 5.25-5.50% on Wednesday, with Chair Jerome Powell saying the committee needs more evidence of cooling inflation before lowering rates.",
        "source_name": "reuters",
        "language": "en",
        "expect": "contextual tier, fed_policy event, moderate-high relevance",
    },
    {
        "title": "China's central bank adds gold reserves for 18th straight month",
        "content": "The People's Bank of China increased its gold holdings by 60,000 troy ounces in April, continuing the longest buying streak on record amid geopolitical tensions and de-dollarization trends.",
        "source_name": "kitco",
        "language": "en",
        "expect": "contextual tier, central_bank_demand event, high relevance",
    },
    {
        "title": "Tesla reports Q1 earnings, misses expectations",
        "content": "Tesla Inc reported first-quarter earnings that fell short of Wall Street expectations, with revenue declining 9% year-over-year amid growing competition in the EV market.",
        "source_name": "reuters",
        "language": "en",
        "expect": "weak tier, stock_market_risk or other, low relevance",
    },
    {
        "title": "Vàng nhẫn trơn 9999 sáng nay 92,5 triệu đồng",
        "content": "Giá vàng nhẫn trơn 9999 tại SJC, DOJI, PNJ đồng loạt niêm yết quanh mốc 92 - 92,5 triệu đồng/lượng.",
        "source_name": "cafef",
        "language": "vi",
        "expect": "direct tier (no verb but is price report!), domestic_market",
    },
]


def main():
    from ml.news_analyzer import analyze_article

    print("=" * 72)
    print("  NEWS ANALYZER -- LOCAL TEST (GPT-5-mini)")
    print("=" * 72)

    for i, tc in enumerate(TEST_ARTICLES, 1):
        print(f"\n{'-' * 72}")
        print(f"  TEST {i}: {tc['title'][:60]}...")
        print(f"  Expected: {tc['expect']}")
        print(f"{'-' * 72}")

        result = analyze_article(
            title=tc["title"],
            content=tc["content"],
            source_name=tc["source_name"],
            language=tc["language"],
        )

        if result is None:
            print("  [FAIL] LLM call FAILED -- would use rule-based fallback")
        else:
            print(f"  sentiment_score : {result.sentiment_score:+.4f}")
            print(f"  relevance_score : {result.relevance_score:.4f}")
            print(f"  impact_score    : {result.impact_score:.4f}")
            print(f"  event_type      : {result.event_type}")
            print(f"  market_scope    : {result.market_scope}")
            print(f"  news_tier       : {result.news_tier}")

    print(f"\n{'=' * 72}")
    print("  TEST COMPLETE")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()
