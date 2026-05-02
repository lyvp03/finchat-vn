# Price Time Range Comparison Plan

## 1. Problem

Current chatbot price context always calls:

```python
get_price_analysis(type_code=_guess_type_code(question), days=7)
```

So a question like:

```text
Giá vàng SJC biến động gì so với tháng trước?
```

is routed to `price_sql`, but the price tool only returns a recent rolling window. The LLM then correctly says the comparison period is missing.

The missing capability is not routing. The missing capability is:

```text
question -> time range / comparison range -> price query for both periods -> structured comparison context
```

## 2. Best Fit For This Project

Use the smallest compatible change:

1. Keep `chatbot.router` focused on intent only.
2. Add a dedicated `chatbot.time_range` parser.
3. Change `context_builder` to pass the original `question` into `tools.price_tool.get_price_analysis`.
4. Extend `get_price_analysis` with optional `question`, while preserving the existing API signature used by `/api/price/history`.
5. Add a new repository method for date-range reads. Do not change `get_historical_data(limit_per_type=...)` because ingest and recompute already depend on it.

This avoids a larger router refactor and keeps API routes backward compatible.

## 3. Target Behavior

Examples:

```text
Giá vàng SJC biến động gì so với tháng trước?
-> price_sql
-> sources.price.type = "comparison"
-> current_period and previous_period exist
```

```text
Giá vàng hôm nay so với hôm qua ra sao?
-> price_sql
-> comparison between today and yesterday
```

```text
Trong 7 ngày gần đây, mã SJC tăng hay giảm?
-> price_sql
-> rolling 7-day analysis
```

If DB lacks one side of the comparison, return a structured missing-period response instead of silently falling back to 7 days.

## 4. Files To Change

```text
backend/chatbot/time_range.py              # new
backend/chatbot/context_builder.py         # pass question to price_tool
backend/tools/price_tool.py                # parse question and return comparison/rolling result
backend/ingest/price/repositories/gold_price_repository.py
backend/chatbot/prompts.py                 # comparison guardrail
backend/tests/test_time_range.py           # new
backend/tests/test_price_tool.py           # new focused unit tests where feasible
backend/tests/test_router.py               # add comparison intent cases
```

Do not change `backend/api/routes/gold_price.py` unless adding optional query params later. Current `/api/price/history?type=...&days=...` should keep working.

## 5. Time Range Parser

Create `backend/chatbot/time_range.py`.

Use rule-based parsing first. Normalize Vietnamese text by lowercasing and removing accents, same style as `chatbot.router`.

Suggested dataclass:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimeRange:
    type: str
    start: datetime | None = None
    end: datetime | None = None
    period_days: int | None = None
    current_start: datetime | None = None
    current_end: datetime | None = None
    previous_start: datetime | None = None
    previous_end: datetime | None = None
```

Supported MVP rules:

```text
compare_previous_month:
  "so với tháng trước", "tháng trước"
  current = first day of current month -> now
  previous = full previous calendar month

compare_previous_week:
  "so với tuần trước", "tuần trước"
  current = last 7 days -> now
  previous = 7 days before current window

compare_yesterday:
  "so với hôm qua", "hôm qua"
  current = today 00:00 -> now
  previous = yesterday 00:00 -> yesterday 23:59:59

rolling_period:
  "30 ngày", "1 tháng gần đây", "một tháng gần đây" -> 30 days
  "7 ngày", "tuần này", "gần đây" -> 7 days
  "3 ngày", "ba ngày" -> 3 days
  default -> 7 days
```

Important: `tuần trước` only means comparison when the wording asks comparison. For a later version, support historical-only queries like “tuần trước giá thế nào?” separately. MVP can treat it as comparison because the current user problem is comparison.

Avoid adding `python-dateutil` unless already installed. Previous month can be computed with standard library:

```python
current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
previous_end = current_start - timedelta(microseconds=1)
previous_start = previous_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
```

## 6. Repository Change

Add a new method, do not replace `get_historical_data`:

```python
def get_data_range(
    self,
    type_code: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    ...
```

Query:

```sql
SELECT *
FROM gold_price FINAL
WHERE type_code = %(type_code)s
  AND ts >= %(start)s
  AND ts <= %(end)s
ORDER BY ts ASC
```

Rationale:

- `get_historical_data(limit_per_type=...)` is used by ingest/recompute and should remain untouched.
- `get_data_range(...)` is purpose-built for chatbot comparisons.

## 7. Price Tool Change

Keep backward compatibility:

```python
def get_price_analysis(
    type_code: str = "SJL1L10",
    days: int = 7,
    question: str | None = None,
) -> Dict[str, Any]:
```

Behavior:

```text
if question is provided:
  time_range = extract_time_range(question)
else:
  time_range = rolling_period(days)

if time_range.type starts with "compare_":
  return comparison result
else:
  return rolling result
```

For rolling analysis, the existing output shape should mostly stay the same, but add:

```json
"type": "rolling",
"time_range_type": "rolling_period"
```

For comparison result:

```json
{
  "ok": true,
  "type": "comparison",
  "time_range_type": "compare_previous_month",
  "type_code": "SJL1L10",
  "metadata": {...},
  "current_period": {...},
  "previous_period": {...},
  "comparison": {
    "latest_vs_previous_avg": ...,
    "current_avg_vs_previous_avg": ...,
    "current_avg_vs_previous_avg_pct": ...,
    "trend": "cao hơn" | "thấp hơn" | "đi ngang"
  }
}
```

If data is missing:

```json
{
  "ok": false,
  "type": "comparison",
  "time_range_type": "compare_previous_month",
  "type_code": "SJL1L10",
  "current_period": {"ok": false, "reason": "..."},
  "previous_period": {"ok": false, "reason": "..."},
  "missing": {
    "current_period": true,
    "previous_period": false
  },
  "error": "Không đủ dữ liệu để so sánh hai kỳ."
}
```

## 8. Period Summary Helper

Add private helpers inside `tools/price_tool.py` first. Extract later only if it grows.

```python
def _summarize_price_period(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"ok": False, "reason": "No price data in this period."}

    first = df.iloc[0]
    latest = df.iloc[-1]
    start_mid = float(first["mid_price"])
    latest_mid = float(latest["mid_price"])
    change = latest_mid - start_mid
    change_pct = change / start_mid * 100 if start_mid else None

    return {
        "ok": True,
        "from": _iso(first["ts"]),
        "to": _iso(latest["ts"]),
        "start_mid_price": start_mid,
        "latest_mid_price": latest_mid,
        "change": change,
        "change_pct": round(change_pct, 4) if change_pct is not None else None,
        "min_mid_price": float(df["mid_price"].min()),
        "max_mid_price": float(df["mid_price"].max()),
        "avg_mid_price": float(df["mid_price"].mean()),
        "records": int(len(df)),
    }
```

## 9. Context Builder Change

Change only this call:

```python
context["price"] = get_price_analysis(
    type_code=_guess_type_code(question),
    days=7,
    question=question,
)
```

This keeps `_guess_type_code()` as-is for now. Symbol extraction can be improved later.

## 10. Prompt Guardrail

Add this to `SYSTEM_PROMPT`:

```text
COMPARISON RULE:
If the user asks a comparison question using phrases such as "so với", "tháng trước", "tuần trước", or "hôm qua", only conclude when CONTEXT.price contains type="comparison" and includes both current_period and previous_period with ok=true.

If one side is missing, clearly state which period is missing. Do not answer a comparison question from a single rolling period.
```

## 11. Tests

### Time Range Tests

```text
extract_time_range("Giá vàng SJC so với tháng trước thế nào?", now=2026-04-28 10:00)
-> compare_previous_month
-> current_start = 2026-04-01 00:00
-> previous_start = 2026-03-01 00:00
-> previous_end date = 2026-03-31
```

```text
extract_time_range("Giá vàng hôm nay so với hôm qua ra sao?", now=2026-04-28 10:00)
-> compare_yesterday
```

```text
extract_time_range("Giá vàng 30 ngày gần đây thế nào?", now=...)
-> rolling_period, period_days=30
```

### Router Tests

Keep `route_question()` returning string:

```text
"Giá vàng SJC biến động gì so với tháng trước?" -> price_sql
"Giá vàng hôm nay so với hôm qua ra sao?" -> price_sql
```

### Price Tool Tests

Use a fake repository/client or monkeypatch repository methods. Do not require ClickHouse for unit tests.

Test:

```text
question mentions previous month
-> get_price_analysis(..., question=question)
-> result["type"] == "comparison"
-> current_period and previous_period are present
```

Also test missing previous period:

```text
previous df empty
-> ok=false
-> missing.previous_period=true
```

## 12. Implementation Phases

### Phase 1: Parser Only

- Add `chatbot/time_range.py`.
- Add `tests/test_time_range.py`.
- No runtime behavior change yet.

### Phase 2: Repository + Price Tool

- Add `GoldPriceRepository.get_data_range(...)`.
- Update `get_price_analysis(..., question=None)`.
- Preserve old `/api/price/history` behavior.

### Phase 3: Chatbot Wiring

- Update `context_builder` to pass `question`.
- Add comparison guardrail to prompt.

### Phase 4: Tests + Manual API Check

Run:

```powershell
cd D:\em_ly\finchat-vn\backend
python -m pytest tests/test_router.py tests/test_time_range.py tests/test_price_tool.py -q
```

Manual check:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body (@{ message = "Giá vàng SJC biến động gì so với tháng trước?"; history = @() } | ConvertTo-Json)
```

Expected:

```text
sources.price.type = comparison
sources.price.current_period exists
sources.price.previous_period exists
```

## 13. Acceptance Checklist

- [ ] Existing `/api/price/history?type=SJL1L10&days=30` still works.
- [ ] Existing price questions without comparison still return rolling analysis.
- [ ] Chatbot comparison question does not silently use 7-day context.
- [ ] `sources.price.type` is `comparison` for "so với tháng trước".
- [ ] Missing comparison period is explicit in `sources.price.missing`.
- [ ] Prompt tells LLM not to answer comparison from rolling-only context.
- [ ] Unit tests for router/time_range/price_tool pass.

## 14. Not In MVP

Do not implement these in the first pass:

- LLM or semantic time parser.
- Full symbol extraction in router.
- Historical-only query semantics like “tuần trước giá thế nào?” without comparison.
- New public API parameters for arbitrary `start/end`.
- Intraday session comparison.

Those can be added after the comparison path is stable.
