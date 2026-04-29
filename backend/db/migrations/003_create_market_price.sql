-- Migration: Tạo bảng market_price cho XAUUSD, USDVND, DXY (future)
-- Engine: ReplacingMergeTree(created_at) — giữ row mới nhất khi merge

CREATE TABLE IF NOT EXISTS market_price (
    ts DateTime,
    symbol String,
    price Float64,
    open Nullable(Float64),
    high Nullable(Float64),
    low Nullable(Float64),
    close Nullable(Float64),
    volume Nullable(Float64),
    source_site String DEFAULT 'yahoo_finance',
    interval String DEFAULT 'daily',
    created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (symbol, ts, interval)
SETTINGS index_granularity = 8192;
