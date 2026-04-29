from datetime import datetime

from rag.chunker import chunk_article


def _article(content: str) -> dict:
    return {
        "id": "news-1",
        "title": "Gold rises on Fed signals",
        "summary": "Gold moved after Fed comments.",
        "content": content,
        "source_name": "Reuters",
        "source_type": "international_news",
        "market_scope": "global",
        "event_type": "fed_policy",
        "published_at": datetime(2026, 4, 28, 8, 30),
        "language": "en",
        "region": "US",
        "symbols": ["GOLD", "USD"],
        "tags": ["fed", "gold_price"],
        "sentiment_score": 0.2,
        "impact_score": 0.7,
        "relevance_score": 0.9,
        "quality_score": 0.8,
        "is_relevant": True,
        "url": "https://example.com/news-1",
    }


def test_short_article_creates_one_contextual_chunk():
    chunks = chunk_article(_article("Gold prices rose after the Fed signaled possible rate cuts."))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.doc_id == "news-1"
    assert chunk.chunk_id == "news-1:0"
    assert "Title: Gold rises on Fed signals" in chunk.embed_text
    assert "Source: Reuters" in chunk.display_text
    assert chunk.metadata["published_at_ts"] > 0
    assert chunk.metadata["symbols"] == ["GOLD", "USD"]


def test_long_article_creates_multiple_chunks_without_mixing_article_boundary():
    paragraph = " ".join(["gold"] * 120)
    content = "\n\n".join([paragraph, paragraph, paragraph, paragraph])

    chunks = chunk_article(_article(content))

    assert len(chunks) > 1
    assert {chunk.doc_id for chunk in chunks} == {"news-1"}
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.chunk_count == len(chunks) for chunk in chunks)


def test_empty_content_is_skipped():
    assert chunk_article(_article("")) == []
