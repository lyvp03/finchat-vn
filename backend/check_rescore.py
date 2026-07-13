"""Check articles needing re-score since 2026-06-05."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.db import get_clickhouse_client

client = get_clickhouse_client()

result = client.query("""
    SELECT count() as total, min(published_at), max(published_at)
    FROM gold_news FINAL
    WHERE published_at >= toDate('2026-06-05')
      AND sentiment_score = 0.0
      AND is_duplicate = 0
""")
row = result.first_row
print(f"Articles to re-score: {row[0]}")
print(f"From: {row[1]}")
print(f"To:   {row[2]}")

result2 = client.query("""
    SELECT toYYYYMM(published_at) as ym, count() as c
    FROM gold_news FINAL
    WHERE published_at >= toDate('2026-06-05')
      AND sentiment_score = 0.0
      AND is_duplicate = 0
    GROUP BY ym ORDER BY ym
""")
print("\nBreakdown by month:")
for r in result2.result_rows:
    print(f"  {r[0]}: {r[1]} articles")

# Also count total articles from same period (to see fallback ratio)
result3 = client.query("""
    SELECT count() as total
    FROM gold_news FINAL
    WHERE published_at >= toDate('2026-06-05')
      AND is_duplicate = 0
""")
total = result3.first_row[0]
print(f"\nTotal articles since 2026-06-05: {total}")
print(f"Fallback ratio: {row[0]}/{total} = {row[0]/total*100:.1f}%" if total > 0 else "No data")
