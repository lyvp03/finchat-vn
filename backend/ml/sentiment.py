"""
Sentiment analysis via GPT-5-mini API.

score_sentiment() trả về float [-1.0, 1.0] từ góc nhìn giá vàng:
  - Dương = bullish cho vàng
  - Âm = bearish cho vàng
"""
import json
import logging

import httpx

from core.config import settings

logger = logging.getLogger("sentiment")


def score_sentiment(text: str, language: str = "en") -> float:
    """Sentiment score [-1.0, 1.0] via GPT-5-mini API.

    Dương = bullish cho vàng, âm = bearish cho vàng.
    """
    if not text or len(text.strip()) < 10:
        return 0.0

    prompt = f"""Analyze this gold market news and return ONLY valid JSON:
{{"score": <float from -1.0 to 1.0>, "signal": "bullish|bearish|neutral"}}

Scoring guide:
- Positive (bullish for gold): gold rises, rate cuts, dollar weakness, inflation, geopolitical risk
- Negative (bearish for gold): gold falls, rate hikes, dollar strength, risk-on sentiment

News ({language}): {text[:500]}"""

    try:
        response = httpx.post(
            f"{settings.GPT_MINI_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GPT_MINI_API_KEY}"},
            json={
                "model": "GPT-5-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1,
                "max_tokens": 1000,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        return round(max(min(float(result["score"]), 1.0), -1.0), 4)
    except Exception as e:
        logger.warning(f"Sentiment API failed: {e}")
        return 0.0
