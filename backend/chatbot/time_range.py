"""Rule-based time range extraction for chatbot price questions."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta


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


def normalize_text(text: str) -> str:
    normalized = text.lower().strip().replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", normalized)


def start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def extract_time_range(question: str, now: datetime | None = None) -> TimeRange:
    now = now or datetime.now()
    text = normalize_text(question)

    if "so voi thang truoc" in text or "thang truoc" in text:
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_end = current_start - timedelta(microseconds=1)
        previous_start = previous_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return TimeRange(
            type="compare_previous_month",
            current_start=current_start,
            current_end=now,
            previous_start=previous_start,
            previous_end=previous_end,
        )

    if "so voi tuan truoc" in text or "tuan truoc" in text:
        current_start = start_of_day(now - timedelta(days=7))
        previous_start = start_of_day(now - timedelta(days=14))
        previous_end = current_start - timedelta(microseconds=1)
        return TimeRange(
            type="compare_previous_week",
            current_start=current_start,
            current_end=now,
            previous_start=previous_start,
            previous_end=previous_end,
        )

    if "so voi hom qua" in text or "hom qua" in text:
        yesterday = now - timedelta(days=1)
        return TimeRange(
            type="compare_yesterday",
            current_start=start_of_day(now),
            current_end=now,
            previous_start=start_of_day(yesterday),
            previous_end=end_of_day(yesterday),
        )

    if "30 ngay" in text or "1 thang gan day" in text or "mot thang gan day" in text:
        return TimeRange(
            type="rolling_period",
            start=now - timedelta(days=30),
            end=now,
            period_days=30,
        )

    if "3 ngay" in text or "ba ngay" in text:
        return TimeRange(
            type="rolling_period",
            start=now - timedelta(days=3),
            end=now,
            period_days=3,
        )

    if "7 ngay" in text or "tuan nay" in text or "gan day" in text:
        return TimeRange(
            type="rolling_period",
            start=now - timedelta(days=7),
            end=now,
            period_days=7,
        )

    return TimeRange(
        type="rolling_period",
        start=now - timedelta(days=7),
        end=now,
        period_days=7,
    )
