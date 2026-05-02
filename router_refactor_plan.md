# Plan sửa Rule-based Intent Router cho Gold Finance Chatbot

## 1. Mục tiêu

Hiện tại router đang route sai một số câu hỏi giá thuần sang `hybrid`, ví dụ:

```text
Trong 7 ngày gần đây, mã SJC tăng hay giảm?
```

Câu này chỉ hỏi dữ liệu giá, nhưng vì có keyword `tăng`, `giảm`, `tuần này`, `biến động`, router dễ hiểu là `hybrid` và gọi thêm RAG news không cần thiết.

Mục tiêu sửa:

- Câu hỏi thuần giá → `price_sql`
- Câu hỏi thuần tin tức → `news_rag`
- Câu hỏi hỏi giá + nguyên nhân/tin tức → `hybrid`
- Câu hỏi ngoài phạm vi → `general`
- Router dễ debug, có thể mở rộng semantic fallback sau này

---

## 2. Vấn đề của router hiện tại

Code hiện tại:

```python
PRICE_KEYWORDS = ("giá", "bao nhiêu", "hôm nay", "mua vào", "bán ra", "sjc", "xauusd", "doji", "btmc")
NEWS_KEYWORDS = ("tin", "vì sao", "tại sao", "ảnh hưởng", "fed", "lãi suất", "cpi", "usd", "địa chính trị", "phân tích")
HYBRID_KEYWORDS = ("tăng", "giảm", "tuần này", "xu hướng", "biến động", "nguyên nhân")
```

Vấn đề chính:

1. `HYBRID_KEYWORDS` đang chứa nhiều từ thuộc nhóm phân tích giá như:
   - `tăng`
   - `giảm`
   - `xu hướng`
   - `biến động`

   Các từ này không nhất thiết là hybrid. Chúng thường chỉ cần dữ liệu giá.

2. `hôm nay`, `tuần này`, `7 ngày gần đây` là time range, không phải intent.

3. `phân tích` không nhất thiết là news. User có thể hỏi:

   ```text
   Phân tích xu hướng giá SJC tuần này
   ```

   Câu này nên là `price_sql` hoặc `hybrid` tùy có hỏi nguyên nhân hay không.

4. Router chỉ trả về string intent, khó debug lý do vì sao route sai.

---

## 3. Nguyên tắc thiết kế mới

Router nên tách signals thành nhiều nhóm rõ ràng:

```text
price_signal       = hỏi giá, mã vàng, chỉ báo, tăng/giảm, mua/bán
news_signal        = hỏi tin tức, bài viết, nguồn tin, sự kiện
cause_signal       = hỏi nguyên nhân, vì sao, do đâu, ảnh hưởng bởi
macro_signal       = Fed, USD, CPI, lãi suất, địa chính trị
time_signal        = hôm nay, 3 ngày, 7 ngày, tuần này, gần đây
out_of_scope       = crypto, stock, non-gold finance
```

Quan trọng:

- `time_signal` không quyết định intent.
- `tăng/giảm/xu hướng/biến động` là price signal, không phải hybrid signal.
- Chỉ route `hybrid` khi có price signal + cause/news/macro signal.

---

## 4. Intent rule mới

### 4.1. `price_sql`

Dùng khi user hỏi dữ liệu giá hoặc kỹ thuật:

```text
Giá SJC hôm nay bao nhiêu?
Trong 7 ngày gần đây, SJC tăng hay giảm?
XAUUSD đang trên hay dưới EMA20?
RSI14 của SJC hiện thế nào?
Spread của DOJI có mở rộng không?
```

Rule:

```text
has_price_signal = True
has_cause_or_news_signal = False
=> price_sql
```

---

### 4.2. `news_rag`

Dùng khi user hỏi tin tức/sự kiện, không hỏi dữ liệu giá cụ thể:

```text
Có tin nào về Fed ảnh hưởng đến vàng không?
Tóm tắt tin vàng gần đây.
Tin Reuters mới nhất về vàng nói gì?
Có tin nào về ngân hàng trung ương mua vàng không?
```

Rule:

```text
has_news_signal = True
has_price_signal = False
=> news_rag
```

---

### 4.3. `hybrid`

Dùng khi user cần kết hợp giá + tin tức/nguyên nhân:

```text
Vì sao giá SJC giảm trong 7 ngày gần đây?
Giá vàng tăng có liên quan đến Fed không?
Tin tức nào giải thích biến động giá vàng tuần này?
XAUUSD giảm có phải do USD mạnh lên không?
```

Rule:

```text
has_price_signal = True
AND has_cause_or_news_signal = True
=> hybrid
```

---

### 4.4. `general`

Dùng khi ngoài phạm vi hoặc câu hỏi giải thích khái niệm chung:

```text
Bitcoin hôm nay thế nào?
Cổ phiếu ngân hàng có nên mua không?
RSI là gì?
Chatbot này dùng dữ liệu nào?
```

Rule:

```text
has_out_of_scope = True
=> general
```

Hoặc:

```text
không match price/news/cause signal
=> general
```

---

## 5. Keyword groups đề xuất

```python
GOLD_SYMBOL_KEYWORDS = (
    "sjc", "sjl1l10", "sj9999", "dohnl", "dohcml", "btsjc", "xauusd",
    "doji", "btmc", "bảo tín minh châu", "vàng miếng", "vàng nhẫn"
)

PRICE_ACTION_KEYWORDS = (
    "giá", "bao nhiêu", "mua vào", "bán ra", "mid", "mid_price",
    "spread", "chênh lệch", "tăng", "giảm", "biến động", "xu hướng",
    "cao nhất", "thấp nhất", "so sánh"
)

TECHNICAL_KEYWORDS = (
    "rsi", "rsi14", "ema", "ema20", "ema50", "macd",
    "bollinger", "daily_return", "daily_return_pct", "indicator", "chỉ báo"
)

NEWS_KEYWORDS = (
    "tin", "tin tức", "bài viết", "nguồn tin", "reuters", "kitco", "vnexpress",
    "sự kiện", "event", "sentiment", "impact", "impact_score", "sentiment_score"
)

CAUSE_KEYWORDS = (
    "vì sao", "tại sao", "do đâu", "nguyên nhân", "lý do",
    "ảnh hưởng", "tác động", "liên quan", "giải thích", "có phải do"
)

MACRO_KEYWORDS = (
    "fed", "lãi suất", "cpi", "lạm phát", "usd", "dxy", "đô la",
    "trái phiếu", "bond yield", "địa chính trị", "chiến tranh",
    "ngân hàng trung ương", "central bank"
)

TIME_KEYWORDS = (
    "hôm nay", "hôm qua", "gần đây", "3 ngày", "7 ngày", "tuần này",
    "tháng này", "phiên gần nhất", "mấy ngày"
)

OUT_OF_SCOPE_KEYWORDS = (
    "bitcoin", "btc", "ethereum", "eth", "crypto", "coin",
    "cổ phiếu", "chứng khoán", "vnindex", "bất động sản"
)
```

---

## 6. Logic router đề xuất

```python
def route_question(question: str) -> str:
    text = normalize_text(question)

    if contains_any(text, OUT_OF_SCOPE_KEYWORDS):
        return "general"

    has_symbol = contains_any(text, GOLD_SYMBOL_KEYWORDS)
    has_price_action = contains_any(text, PRICE_ACTION_KEYWORDS)
    has_technical = contains_any(text, TECHNICAL_KEYWORDS)
    has_news = contains_any(text, NEWS_KEYWORDS)
    has_cause = contains_any(text, CAUSE_KEYWORDS)
    has_macro = contains_any(text, MACRO_KEYWORDS)

    has_price_signal = has_symbol or has_price_action or has_technical
    has_cause_or_news_signal = has_news or has_cause or has_macro

    # Price + cause/news/macro => hybrid
    if has_price_signal and has_cause_or_news_signal:
        return "hybrid"

    # Pure price => price_sql
    if has_price_signal:
        return "price_sql"

    # Pure news/macro/cause => news_rag
    if has_cause_or_news_signal:
        return "news_rag"

    return "general"
```

---

## 7. Nên trả object thay vì string

Phiên bản hiện tại trả:

```python
"hybrid"
```

Nên nâng cấp thành:

```python
{
    "intent": "price_sql",
    "confidence": 0.9,
    "reason": "Question asks price movement over a time range without asking for news or causes.",
    "signals": {
        "has_price_signal": True,
        "has_news_signal": False,
        "has_cause_signal": False,
        "has_macro_signal": False
    }
}
```

Lợi ích:

- Dễ debug khi route sai.
- Có thể log router decision.
- Có thể thêm semantic fallback sau này.
- Tool layer có thể dùng signals/time_range/symbols.

Nếu chưa muốn sửa nhiều code, có thể giữ `route_question()` trả string và thêm hàm mới:

```python
def analyze_question(question: str) -> RouteResult:
    ...


def route_question(question: str) -> str:
    return analyze_question(question).intent
```

---

## 8. Semantic fallback sau này

Sau khi rule-based ổn, có thể thêm semantic fallback cho câu mơ hồ:

```text
Thị trường vàng tuần này có gì đáng chú ý?
Vàng đang chịu áp lực gì?
Tình hình vàng hiện tại thế nào?
```

Logic:

```text
Nếu rule confidence cao >= 0.8 → dùng rule
Nếu rule confidence thấp → gọi semantic/LLM classifier
Nếu semantic cũng thấp → default hybrid
```

Không nên dùng semantic thay thế hoàn toàn rule-based vì router tài chính cần dễ kiểm soát và debug.

---

## 9. Test cases bắt buộc

### 9.1. Price SQL

```text
Giá SJC hôm nay bao nhiêu?
=> price_sql
```

```text
Trong 7 ngày gần đây, mã SJC tăng hay giảm?
=> price_sql
```

```text
XAUUSD đang có xu hướng tăng hay giảm theo EMA20?
=> price_sql
```

```text
Spread của DOJI trong 3 phiên gần nhất thế nào?
=> price_sql
```

---

### 9.2. News RAG

```text
Có tin nào về Fed ảnh hưởng đến vàng không?
=> news_rag
```

```text
Tóm tắt tin vàng gần đây từ Reuters.
=> news_rag
```

```text
Có bài nào nói về ngân hàng trung ương mua vàng không?
=> news_rag
```

---

### 9.3. Hybrid

```text
Vì sao giá SJC giảm trong 7 ngày gần đây?
=> hybrid
```

```text
Giá vàng tăng có liên quan đến Fed không?
=> hybrid
```

```text
Tin tức nào giải thích biến động giá vàng tuần này?
=> hybrid
```

```text
XAUUSD giảm có phải do USD mạnh lên không?
=> hybrid
```

---

### 9.4. General / out-of-scope

```text
Bitcoin hôm nay thế nào?
=> general
```

```text
Cổ phiếu ngân hàng có nên mua không?
=> general
```

```text
RSI là gì?
=> general
```

---

## 10. Unit test gợi ý

Tạo file:

```text
tests/chatbot/test_router.py
```

Ví dụ:

```python
import pytest

from chatbot.router import route_question


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Giá SJC hôm nay bao nhiêu?", "price_sql"),
        ("Trong 7 ngày gần đây, mã SJC tăng hay giảm?", "price_sql"),
        ("XAUUSD đang có xu hướng tăng hay giảm theo EMA20?", "price_sql"),
        ("Spread của DOJI trong 3 phiên gần nhất thế nào?", "price_sql"),
        ("Có tin nào về Fed ảnh hưởng đến vàng không?", "news_rag"),
        ("Tóm tắt tin vàng gần đây từ Reuters.", "news_rag"),
        ("Vì sao giá SJC giảm trong 7 ngày gần đây?", "hybrid"),
        ("Giá vàng tăng có liên quan đến Fed không?", "hybrid"),
        ("Tin tức nào giải thích biến động giá vàng tuần này?", "hybrid"),
        ("Bitcoin hôm nay thế nào?", "general"),
        ("Cổ phiếu ngân hàng có nên mua không?", "general"),
    ],
)
def test_route_question(question, expected):
    assert route_question(question) == expected
```

---

## 11. Implementation phases

### Phase 1: Sửa keyword groups

- Tách `HYBRID_KEYWORDS` thành:
  - `CAUSE_KEYWORDS`
  - `MACRO_KEYWORDS`
- Chuyển `tăng`, `giảm`, `xu hướng`, `biến động` sang `PRICE_ACTION_KEYWORDS`.
- Không dùng `TIME_KEYWORDS` để quyết định hybrid.

### Phase 2: Sửa logic route

- Tính signals riêng.
- Route theo rule:

```text
price + cause/news/macro => hybrid
price only              => price_sql
news/cause/macro only   => news_rag
out of scope            => general
fallback                => general
```

### Phase 3: Thêm tests

- Viết unit test cho các câu hỏi phổ biến.
- Chạy lại test mỗi lần sửa keyword.

### Phase 4: Thêm debug result

- Thêm `RouteResult` trả intent + confidence + reason + signals.
- Log router decision trong API/chat orchestrator.

### Phase 5: Semantic fallback

- Chỉ thêm sau khi rule-based ổn.
- Dùng cho câu hỏi mơ hồ.
- Default `hybrid` nếu không chắc nhưng vẫn là câu hỏi về thị trường vàng.

---

## 12. Code refactor gợi ý

```python
"""Rule-based intent router for gold finance questions."""

from dataclasses import dataclass


GOLD_SYMBOL_KEYWORDS = (
    "sjc", "sjl1l10", "sj9999", "dohnl", "dohcml", "btsjc", "xauusd",
    "doji", "btmc", "bảo tín minh châu", "vàng miếng", "vàng nhẫn", "vàng"
)

PRICE_ACTION_KEYWORDS = (
    "giá", "bao nhiêu", "mua vào", "bán ra", "mid", "mid_price",
    "spread", "chênh lệch", "tăng", "giảm", "biến động", "xu hướng",
    "cao nhất", "thấp nhất", "so sánh"
)

TECHNICAL_KEYWORDS = (
    "rsi", "rsi14", "ema", "ema20", "ema50", "macd",
    "bollinger", "daily_return", "daily_return_pct", "indicator", "chỉ báo"
)

NEWS_KEYWORDS = (
    "tin", "tin tức", "bài viết", "nguồn tin", "reuters", "kitco", "vnexpress",
    "sự kiện", "event", "sentiment", "impact", "impact_score", "sentiment_score"
)

CAUSE_KEYWORDS = (
    "vì sao", "tại sao", "do đâu", "nguyên nhân", "lý do",
    "ảnh hưởng", "tác động", "liên quan", "giải thích", "có phải do"
)

MACRO_KEYWORDS = (
    "fed", "lãi suất", "cpi", "lạm phát", "usd", "dxy", "đô la",
    "trái phiếu", "bond yield", "địa chính trị", "chiến tranh",
    "ngân hàng trung ương", "central bank"
)

OUT_OF_SCOPE_KEYWORDS = (
    "bitcoin", "btc", "ethereum", "eth", "crypto", "coin",
    "cổ phiếu", "chứng khoán", "vnindex", "bất động sản"
)


@dataclass(frozen=True)
class RouteResult:
    intent: str
    confidence: float
    reason: str
    signals: dict


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def normalize_text(question: str) -> str:
    return question.lower().strip()


def analyze_question(question: str) -> RouteResult:
    text = normalize_text(question)

    has_out_of_scope = contains_any(text, OUT_OF_SCOPE_KEYWORDS)
    if has_out_of_scope:
        return RouteResult(
            intent="general",
            confidence=0.95,
            reason="Question contains out-of-scope finance keywords.",
            signals={"has_out_of_scope": True},
        )

    has_symbol = contains_any(text, GOLD_SYMBOL_KEYWORDS)
    has_price_action = contains_any(text, PRICE_ACTION_KEYWORDS)
    has_technical = contains_any(text, TECHNICAL_KEYWORDS)
    has_news = contains_any(text, NEWS_KEYWORDS)
    has_cause = contains_any(text, CAUSE_KEYWORDS)
    has_macro = contains_any(text, MACRO_KEYWORDS)

    has_price_signal = has_symbol or has_price_action or has_technical
    has_cause_or_news_signal = has_news or has_cause or has_macro

    signals = {
        "has_symbol": has_symbol,
        "has_price_action": has_price_action,
        "has_technical": has_technical,
        "has_news": has_news,
        "has_cause": has_cause,
        "has_macro": has_macro,
        "has_price_signal": has_price_signal,
        "has_cause_or_news_signal": has_cause_or_news_signal,
    }

    if has_price_signal and has_cause_or_news_signal:
        return RouteResult(
            intent="hybrid",
            confidence=0.9,
            reason="Question combines price signal with news/cause/macro signal.",
            signals=signals,
        )

    if has_price_signal:
        return RouteResult(
            intent="price_sql",
            confidence=0.9,
            reason="Question asks about price, movement, symbol, or technical indicator only.",
            signals=signals,
        )

    if has_cause_or_news_signal:
        return RouteResult(
            intent="news_rag",
            confidence=0.85,
            reason="Question asks about news, causes, or macro events without explicit price data request.",
            signals=signals,
        )

    return RouteResult(
        intent="general",
        confidence=0.6,
        reason="No clear price or news signal found.",
        signals=signals,
    )


def route_question(question: str) -> str:
    return analyze_question(question).intent
```

---

## 13. Expected result sau khi sửa

Trước khi sửa:

```text
Trong 7 ngày gần đây, mã SJC tăng hay giảm?
=> hybrid
```

Sau khi sửa:

```text
Trong 7 ngày gần đây, mã SJC tăng hay giảm?
=> price_sql
```

Trước khi sửa:

```text
Tin tức nào giải thích biến động giá vàng tuần này?
=> có thể news_rag hoặc hybrid không ổn định
```

Sau khi sửa:

```text
Tin tức nào giải thích biến động giá vàng tuần này?
=> hybrid
```

---

## 14. Kết luận

Việc sửa router nên tập trung vào 3 điểm:

1. Không coi `tăng`, `giảm`, `xu hướng`, `biến động`, `tuần này` là hybrid mặc định.
2. Chỉ route `hybrid` khi câu hỏi có cả price signal và cause/news/macro signal.
3. Thêm test cases để đảm bảo các câu hỏi thực tế không bị route sai.

Sau khi router ổn, mới tiếp tục nâng cấp:

- time range extraction
- Chroma metadata filter
- chunk-level RAG
- semantic fallback cho câu hỏi mơ hồ
