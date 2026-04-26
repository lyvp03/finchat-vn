from core.db import get_clickhouse_client

c = get_clickhouse_client()

# News date range
r = c.query("SELECT min(published_at), max(published_at), count() FROM gold_news FINAL")
print(f"News: {r.result_rows[0][2]} articles, {r.result_rows[0][0]} -> {r.result_rows[0][1]}")

# Price date range
r = c.query("SELECT min(ts), max(ts), count() FROM gold_price FINAL")
print(f"Price: {r.result_rows[0][2]} rows, {r.result_rows[0][0]} -> {r.result_rows[0][1]}")

# News per month
r = c.query("SELECT toYYYYMM(published_at) as m, count() FROM gold_news FINAL GROUP BY m ORDER BY m")
print("\nNews by month:")
for row in r.result_rows:
    print(f"  {row[0]}: {row[1]}")

# Overlap window
r = c.query("""
    SELECT count() FROM gold_news FINAL
    WHERE toDate(published_at) >= (SELECT min(toDate(ts)) FROM gold_price FINAL)
    AND toDate(published_at) <= (SELECT max(toDate(ts)) FROM gold_price FINAL)
""")
print(f"\nNews trong window price (90 ngày): {r.result_rows[0][0]}")
