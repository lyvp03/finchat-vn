"""
Unified news analysis via GPT-5-mini API.

Replaces 4 separate hardcoded scoring/classification functions with a single
LLM call that returns structured JSON.  Falls back to rule-based heuristics
when the API is unavailable.

Output fields
─────────────
  sentiment_score  : float [-1.0, 1.0]   — bullish(+) / bearish(-) for gold
  relevance_score  : float [0.0, 1.0]    — how related to gold market
  impact_score     : float [0.0, 1.0]    — expected price-move magnitude
  event_type       : str                 — classified event category
  market_scope     : str                 — domestic / international / mixed
  news_tier        : str                 — direct / contextual / weak
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from core.config import settings

logger = logging.getLogger("news_analyzer")

# ── Valid enum values (for validation) ────────────────────────────────────────

_VALID_EVENT_TYPES = {
    "domestic_market", "fed_policy", "inflation_data", "usd_movement",
    "bond_yield", "geopolitical_risk", "tariff_trade", "central_bank_demand",
    "gold_price_update", "economic_growth", "stock_market_risk", "other",
}
_VALID_MARKET_SCOPES = {"domestic", "international", "mixed"}
_VALID_NEWS_TIERS = {"direct", "contextual", "weak"}


@dataclass
class NewsAnalysis:
    """Structured result from LLM or fallback."""
    sentiment_score: float = 0.0
    relevance_score: float = 0.0
    impact_score: float = 0.0
    event_type: str = "other"
    market_scope: str = "international"
    news_tier: str = "weak"


# ── Prompt with detailed rubrics ─────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a gold market analyst AI. You analyze news articles and return structured JSON scores.

You MUST follow the rubrics below EXACTLY. Do NOT guess — use the criteria.

## RUBRIC 1: sentiment_score (float, -1.0 to 1.0)
How this news affects GOLD PRICE direction.
| Score Range     | Meaning                        | Examples                                           |
|-----------------|--------------------------------|----------------------------------------------------|
| +0.7 to +1.0   | Strongly bullish for gold      | Fed cuts rates unexpectedly, war escalation, USD crashes, inflation surges |
| +0.3 to +0.69  | Moderately bullish             | Rate cut expectations rise, mild geopolitical tension, dollar weakens |
| +0.01 to +0.29 | Slightly bullish               | Gold price ticks up, minor safe-haven flow         |
| 0.0             | Neutral / no clear impact      | General market recap, unrelated economic data       |
| -0.01 to -0.29 | Slightly bearish               | Gold dips slightly, mild risk-on sentiment          |
| -0.3 to -0.69  | Moderately bearish             | Strong jobs data, rate hike expectations, USD rallies |
| -0.7 to -1.0   | Strongly bearish for gold      | Fed hikes aggressively, gold crashes, strong risk-on rally |

## RUBRIC 2: relevance_score (float, 0.0 to 1.0)
How directly related to the gold market.
| Score Range   | Criteria                                                              |
|---------------|-----------------------------------------------------------------------|
| 0.8 - 1.0     | Article is PRIMARILY about gold price, gold trading, gold reserves    |
| 0.6 - 0.79    | Gold is a MAJOR topic (mentioned in title + discussed in detail)      |
| 0.4 - 0.59    | Gold-adjacent: Fed policy, USD, inflation, central bank buying — gold mentioned or strongly implied |
| 0.2 - 0.39    | Loosely related: general macro/geopolitical that COULD affect gold    |
| 0.0 - 0.19    | Not about gold: crypto, stocks, unrelated commodities, lifestyle     |

## RUBRIC 3: impact_score (float, 0.0 to 1.0)
Expected magnitude of gold price reaction.
| Score Range   | Criteria                                                              |
|---------------|-----------------------------------------------------------------------|
| 0.8 - 1.0     | Market-moving event: surprise rate decision, war outbreak, gold crash/surge >3% |
| 0.6 - 0.79    | Significant: scheduled FOMC/CPI/NFP release with unexpected result    |
| 0.4 - 0.59    | Moderate: expected macro data, gradual trend shifts, central bank buying |
| 0.2 - 0.39    | Minor: routine updates, analyst opinions, scheduled data as-expected  |
| 0.0 - 0.19    | Negligible: old news, commentary, tangentially related               |

## RUBRIC 4: event_type (string, pick ONE)
| Value                | When to use                                                         |
|----------------------|---------------------------------------------------------------------|
| domestic_market      | Vietnamese gold market: SJC, DOJI, PNJ, BTMC, vàng miếng/nhẫn prices |
| fed_policy           | Federal Reserve decisions, FOMC meetings, interest rate changes      |
| inflation_data       | CPI, PCE, inflation reports                                         |
| usd_movement         | USD/DXY strength or weakness                                        |
| bond_yield           | Treasury/bond yield changes                                         |
| geopolitical_risk    | Wars, conflicts, sanctions, geopolitical tensions                   |
| tariff_trade         | Tariffs, trade wars, trade policy                                   |
| central_bank_demand  | Central banks buying/selling gold reserves                          |
| gold_price_update    | International gold price reporting (XAUUSD, spot, futures, COMEX)   |
| economic_growth      | GDP, recession, employment data (non-NFP)                           |
| stock_market_risk    | Stock market crashes, equity risk-off                               |
| other                | None of the above                                                   |

## RUBRIC 5: market_scope (string, pick ONE)
| Value          | When to use                                                           |
|----------------|-----------------------------------------------------------------------|
| domestic       | About Vietnam gold market specifically (SJC, DOJI, giá vàng trong nước) |
| international  | About global/US/world gold market (XAUUSD, COMEX, Fed, geopolitics)   |
| mixed          | Covers BOTH Vietnamese AND international gold markets                 |

## RUBRIC 6: news_tier (string, pick ONE)
| Value       | When to use                                                              |
|-------------|--------------------------------------------------------------------------|
| direct      | Headline/article is DIRECTLY about gold price change (giá vàng tăng/giảm, gold rises/falls, gold price today) |
| contextual  | About factors that AFFECT gold (Fed, USD, inflation, geopolitics) but not directly a gold price report |
| weak        | Loosely related, opinion pieces, general market commentary               |"""

_USER_PROMPT_TEMPLATE = """Analyze this gold market news and return ONLY valid JSON (no markdown, no explanation):
{{"sentiment_score": <float>, "relevance_score": <float>, "impact_score": <float>, "event_type": "<string>", "market_scope": "<string>", "news_tier": "<string>"}}

Source: {source_name} ({language})
Title: {title}
Content: {content}"""


def _clamp(value: float, lo: float, hi: float) -> float:
    return round(max(min(value, hi), lo), 4)


def _validate_analysis(raw: dict) -> Optional[NewsAnalysis]:
    """Parse and validate raw JSON from LLM into a NewsAnalysis."""
    try:
        sentiment = _clamp(float(raw.get("sentiment_score", 0)), -1.0, 1.0)
        relevance = _clamp(float(raw.get("relevance_score", 0)), 0.0, 1.0)
        impact = _clamp(float(raw.get("impact_score", 0)), 0.0, 1.0)

        event_type = str(raw.get("event_type", "other")).lower().strip()
        if event_type not in _VALID_EVENT_TYPES:
            event_type = "other"

        market_scope = str(raw.get("market_scope", "international")).lower().strip()
        if market_scope not in _VALID_MARKET_SCOPES:
            market_scope = "international"

        news_tier = str(raw.get("news_tier", "weak")).lower().strip()
        if news_tier not in _VALID_NEWS_TIERS:
            news_tier = "weak"

        return NewsAnalysis(
            sentiment_score=sentiment,
            relevance_score=relevance,
            impact_score=impact,
            event_type=event_type,
            market_scope=market_scope,
            news_tier=news_tier,
        )
    except (ValueError, TypeError, KeyError) as e:
        logger.warning("Failed to validate LLM response: %s", e)
        return None


def analyze_article(
    title: str,
    content: str,
    source_name: str = "",
    language: str = "vi",
) -> Optional[NewsAnalysis]:
    """Call GPT-5-mini with detailed rubrics. Returns None on failure (caller uses fallback)."""
    text = f"{title}. {content or ''}"
    if not text or len(text.strip()) < 10:
        return None

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        source_name=source_name or "unknown",
        language=language,
        title=title[:200],
        content=(content or "")[:800],
    )

    try:
        response = httpx.post(
            f"{settings.GPT_MINI_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GPT_MINI_API_KEY}"},
            json={
                "model": "GPT-5-mini",
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 1,
                "max_tokens": 1000,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        raw_content = response.json()["choices"][0]["message"]["content"]

        # Strip markdown fences if LLM wraps in ```json ... ```
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(cleaned)
        return _validate_analysis(result)

    except Exception as e:
        logger.warning("News analysis LLM call failed: %s", e)
        return None
