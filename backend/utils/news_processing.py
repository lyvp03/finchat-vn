"""
News preprocessing — public API facade.

All logic has been split into focused submodules:
  - utils.text_cleaning     → clean_text, sha256_hash
  - utils.news_scoring      → quality, relevance, impact, symbols, tags, entities
  - utils.news_classification → market_scope, event_type, news_tier

This file re-exports everything so existing imports continue to work.
"""

# Text cleaning
from utils.text_cleaning import clean_text, sha256_hash

# Scoring & extraction
from utils.news_scoring import (
    compute_quality_score,
    compute_relevance_score,
    compute_impact_score,
    extract_symbols,
    extract_tags,
    extract_entities,
)

# Classification
from utils.news_classification import (
    classify_market_scope,
    classify_event_type,
    classify_news_tier,
)

__all__ = [
    "clean_text",
    "sha256_hash",
    "compute_quality_score",
    "compute_relevance_score",
    "compute_impact_score",
    "extract_symbols",
    "extract_tags",
    "extract_entities",
    "classify_market_scope",
    "classify_event_type",
    "classify_news_tier",
]
