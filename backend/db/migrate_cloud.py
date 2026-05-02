"""
Run once to create all tables on ClickHouse Cloud.
Usage: python backend/db/migrate_cloud.py
"""
import urllib.request
import base64
import sys

HOST = "https://d563to70mv.ap-southeast-1.aws.clickhouse.cloud:8443"
USER = "default"
PASSWORD = "p.wdKTsc9Y6_N"

creds = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {creds}", "Content-Type": "text/plain"}

MIGRATIONS = [
    ("drop gold_price", "DROP TABLE IF EXISTS gold_price"),
    ("gold_price", """
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
ORDER BY (ts, type_code)
"""),
    ("gold_news", """
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
SETTINGS index_granularity = 8192
"""),
    ("market_price", """
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
SETTINGS index_granularity = 8192
"""),
    ("verify", "SHOW TABLES"),
]


def run_sql(label: str, sql: str) -> None:
    req = urllib.request.Request(HOST, data=sql.strip().encode(), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            result = r.read().decode().strip()
            print(f"  ✅ {label}: {result or 'done'}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # Ignore "column already exists" errors
        if "already exists" in body:
            print(f"  ⏭  {label}: already exists, skipping")
        else:
            print(f"  ❌ {label} HTTP {e.code}: {body[:300]}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    print("Running migrations on ClickHouse Cloud...")
    for label, sql in MIGRATIONS:
        run_sql(label, sql)

    # Hotfix: add columns that were added after initial migration
    hotfixes = [
        ("add news_tier column",
         "ALTER TABLE gold_news ADD COLUMN IF NOT EXISTS news_tier String DEFAULT ''"),
    ]
    print("\nRunning hotfixes...")
    for label, sql in hotfixes:
        run_sql(label, sql)

    print("\nAll migrations completed!")

