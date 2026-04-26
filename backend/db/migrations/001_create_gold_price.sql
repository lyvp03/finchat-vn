-- Migration: Tạo bảng gold_price
-- Engine: ReplacingMergeTree(created_at) — giữ row mới nhất khi merge

CREATE TABLE IF NOT EXISTS gold_price (
    ts DateTime,
    type_code String,
    brand String,
    gold_type String,
    buy_price Float64,
    sell_price Float64,
    mid_price Float64,
    spread Float64,
    spread_pct Float64 DEFAULT 0,
    price_change Float64 DEFAULT 0,
    daily_return_pct Float64 DEFAULT 0,
    ema20 Float64,
    ema50 Float64,
    macd Float64,
    macd_signal Float64,
    macd_hist Float64,
    rsi14 Float64,
    source_site String DEFAULT 'vang.today',
    created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (ts, type_code);
