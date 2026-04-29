from datetime import datetime

from chatbot.time_range import extract_time_range


def test_extract_compare_previous_month():
    now = datetime(2026, 4, 28, 10, 0, 0)
    result = extract_time_range("Giá vàng SJC so với tháng trước thế nào?", now=now)

    assert result.type == "compare_previous_month"
    assert result.current_start == datetime(2026, 4, 1, 0, 0, 0)
    assert result.current_end == now
    assert result.previous_start == datetime(2026, 3, 1, 0, 0, 0)
    assert result.previous_end.date().isoformat() == "2026-03-31"


def test_extract_compare_yesterday():
    now = datetime(2026, 4, 28, 10, 0, 0)
    result = extract_time_range("Giá vàng hôm nay so với hôm qua ra sao?", now=now)

    assert result.type == "compare_yesterday"
    assert result.current_start == datetime(2026, 4, 28, 0, 0, 0)
    assert result.previous_start == datetime(2026, 4, 27, 0, 0, 0)
    assert result.previous_end.date().isoformat() == "2026-04-27"


def test_extract_rolling_30_days():
    now = datetime(2026, 4, 28, 10, 0, 0)
    result = extract_time_range("Giá vàng 30 ngày gần đây thế nào?", now=now)

    assert result.type == "rolling_period"
    assert result.period_days == 30
