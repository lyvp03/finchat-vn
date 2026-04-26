-- Migration: Tạo bảng gold_news
-- Engine: ReplacingMergeTree (tự động gộp dòng trùng theo ORDER BY id)

CREATE TABLE IF NOT EXISTS gold_news (
    id String,
    title String,
    summary String,
    content String,
    source_name String,
    source_type String,
    author String,
    url String,
    canonical_url String,
    published_at DateTime,
    crawled_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now(),
    category String,
    language String DEFAULT 'vi',
    region String,
    event_type String,
    symbols Array(String),
    tags Array(String),
    entities Array(String),
    sentiment_score Float32 DEFAULT 0,
    impact_score Float32 DEFAULT 0,
    relevance_score Float32 DEFAULT 0,
    content_hash String,
    title_hash String,
    is_duplicate Bool DEFAULT false,
    quality_score Float32 DEFAULT 1,
    is_relevant Bool DEFAULT true,
    market_scope String DEFAULT '',
    raw_payload String,
    extra_metadata String
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id
SETTINGS index_granularity = 8192;
