"""Article-aware chunking for gold news RAG."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from core.config import settings


@dataclass(frozen=True)
class NewsChunk:
    point_id: str
    doc_id: str
    chunk_id: str
    chunk_index: int
    chunk_count: int
    embed_text: str
    display_text: str
    metadata: Dict[str, Any]


def chunk_article(article: Dict[str, Any]) -> List[NewsChunk]:
    content = _clean_text(article.get("content") or "")
    if not article.get("id") or not content:
        return []

    paragraphs = split_paragraphs(content)
    if not paragraphs:
        return []

    if count_tokens(content) <= settings.RAG_SHORT_ARTICLE_TOKENS:
        content_chunks = [content]
    else:
        content_chunks = _window_paragraphs(paragraphs)

    content_chunks = [
        chunk for chunk in content_chunks
        if count_tokens(chunk) >= settings.RAG_MIN_CHUNK_TOKENS or len(content_chunks) == 1
    ]

    total = len(content_chunks)
    return [
        build_chunk(article=article, content_chunk=content_chunk, chunk_index=index, chunk_count=total)
        for index, content_chunk in enumerate(content_chunks)
    ]


def split_paragraphs(text: str) -> List[str]:
    text = _clean_text(text)
    if not text:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]


def count_tokens(text: str) -> int:
    return len(text.split())


def build_chunk(
    article: Dict[str, Any],
    content_chunk: str,
    chunk_index: int,
    chunk_count: int,
) -> NewsChunk:
    doc_id = str(article["id"])
    chunk_id = f"{doc_id}:{chunk_index}"
    metadata = _metadata(article, content_chunk, chunk_id, chunk_index, chunk_count)
    embed_text = _embed_text(metadata)
    display_text = _display_text(metadata)
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

    return NewsChunk(
        point_id=point_id,
        doc_id=doc_id,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        embed_text=embed_text,
        display_text=display_text,
        metadata=metadata,
    )


def _window_paragraphs(paragraphs: List[str]) -> List[str]:
    max_tokens = settings.RAG_MAX_CHUNK_TOKENS
    overlap = max(0, settings.RAG_CHUNK_OVERLAP_PARAGRAPHS)
    chunks: List[List[str]] = []
    current: List[str] = []

    for paragraph in paragraphs:
        candidate = current + [paragraph]
        if count_tokens("\n\n".join(candidate)) <= max_tokens:
            current.append(paragraph)
            continue

        if current:
            chunks.append(current)
            current = current[-overlap:] if overlap else []

        if count_tokens(paragraph) > max_tokens:
            chunks.extend([[part] for part in _split_long_paragraph(paragraph, max_tokens)])
            current = []
        else:
            current.append(paragraph)

    if current:
        chunks.append(current)

    return ["\n\n".join(chunk).strip() for chunk in chunks if "\n\n".join(chunk).strip()]


def _split_long_paragraph(paragraph: str, max_tokens: int) -> List[str]:
    words = paragraph.split()
    return [
        " ".join(words[index:index + max_tokens])
        for index in range(0, len(words), max_tokens)
    ]


def _metadata(
    article: Dict[str, Any],
    content_chunk: str,
    chunk_id: str,
    chunk_index: int,
    chunk_count: int,
) -> Dict[str, Any]:
    published_at = article.get("published_at")
    published_at_iso = published_at.isoformat() if hasattr(published_at, "isoformat") else str(published_at or "")
    published_at_ts = int(published_at.timestamp()) if isinstance(published_at, datetime) else None

    return {
        "doc_id": str(article.get("id", "")),
        "chunk_id": chunk_id,
        "chunk_index": int(chunk_index),
        "chunk_count": int(chunk_count),
        "title": str(article.get("title") or ""),
        "summary": str(article.get("summary") or ""),
        "content_chunk": content_chunk,
        "source_name": str(article.get("source_name") or ""),
        "source_type": str(article.get("source_type") or ""),
        "market_scope": str(article.get("market_scope") or ""),
        "event_type": str(article.get("event_type") or ""),
        "published_at": published_at_iso,
        "published_at_ts": published_at_ts,
        "language": str(article.get("language") or ""),
        "region": str(article.get("region") or ""),
        "symbols": list(article.get("symbols") or []),
        "tags": list(article.get("tags") or []),
        "sentiment_score": float(article.get("sentiment_score") or 0),
        "impact_score": float(article.get("impact_score") or 0),
        "relevance_score": float(article.get("relevance_score") or 0),
        "quality_score": float(article.get("quality_score") or 0),
        "is_relevant": bool(article.get("is_relevant", True)),
        "news_tier": str(article.get("news_tier") or "contextual"),
        "url": str(article.get("url") or ""),
    }


def _embed_text(metadata: Dict[str, Any]) -> str:
    return (
        f"Title: {metadata['title']}\n"
        f"Summary: {metadata['summary']}\n"
        f"Source: {metadata['source_name']}\n"
        f"Published at: {metadata['published_at']}\n"
        f"Market scope: {metadata['market_scope']}\n"
        f"Event type: {metadata['event_type']}\n"
        f"Symbols: {metadata['symbols']}\n\n"
        f"Content:\n{metadata['content_chunk']}"
    ).strip()


def _display_text(metadata: Dict[str, Any]) -> str:
    return (
        f"Title: {metadata['title']}\n"
        f"Source: {metadata['source_name']}\n"
        f"Published at: {metadata['published_at']}\n"
        f"URL: {metadata['url']}\n\n"
        f"{metadata['content_chunk']}"
    ).strip()


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
