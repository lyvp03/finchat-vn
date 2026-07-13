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
    is_fallback: bool = False


def normalize_text(text: str) -> str:
    normalized = text.lower().strip().replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", normalized)


def start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


DATE_PATTERN = r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b"

def extract_specific_dates(text: str, now: datetime) -> list[datetime]:
    """Tìm các mốc thời gian cụ thể (ngày, hôm nay, hôm qua)."""
    dates = []
    
    # Text already normalized in extract_time_range (hom nay, hom qua)
    if any(k in text for k in ("hom nay", "homnay", "hien tai", "bay gio")):
        dates.append(start_of_day(now))
    if any(k in text for k in ("hom qua", "homqua")):
        dates.append(start_of_day(now - timedelta(days=1)))
        
    matches = re.findall(DATE_PATTERN, text)
    for day_str, month_str, year_str in matches:
        try:
            day = int(day_str)
            month = int(month_str)
            y = int(year_str) if year_str else now.year
            if y < 100:
                y += 2000
            
            # Basic validation
            if not (1 <= month <= 12 and 1 <= day <= 31):
                continue
                
            dt = datetime(y, month, day)
            # If no year given and date is in future, assume last year
            if not year_str and dt > now:
                dt = dt.replace(year=y - 1)
            
            dates.append(dt)
        except ValueError:
            continue
            
    # Remove duplicates, keep chronological order
    unique_dates = []
    for d in dates:
        if d not in unique_dates:
            unique_dates.append(d)
    return sorted(unique_dates)

def extract_time_range(question: str, now: datetime | None = None) -> TimeRange:
    now = now or datetime.now()
    text = normalize_text(question)

    specific_dates = extract_specific_dates(text, now)
    if len(specific_dates) >= 2:
        return TimeRange(
            type="specific_comparison",
            current_start=specific_dates[1],
            current_end=end_of_day(specific_dates[1]),
            previous_start=specific_dates[0],
            previous_end=end_of_day(specific_dates[0]),
            is_fallback=False
        )
    elif len(specific_dates) == 1:
        return TimeRange(
            type="specific_single",
            start=specific_dates[0],
            end=end_of_day(specific_dates[0]),
            period_days=1,
            is_fallback=False
        )

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
            is_fallback=False
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
            is_fallback=False
        )

    if "so voi hom qua" in text or "hom qua" in text:
        yesterday = now - timedelta(days=1)
        return TimeRange(
            type="compare_yesterday",
            current_start=start_of_day(now),
            current_end=now,
            previous_start=start_of_day(yesterday),
            previous_end=end_of_day(yesterday),
            is_fallback=False
        )

    if "30 ngay" in text or "1 thang gan day" in text or "mot thang gan day" in text:
        return TimeRange(
            type="rolling_period",
            start=now - timedelta(days=30),
            end=now,
            period_days=30,
            is_fallback=False
        )

    if "3 ngay" in text or "ba ngay" in text:
        return TimeRange(
            type="rolling_period",
            start=now - timedelta(days=3),
            end=now,
            period_days=3,
            is_fallback=False
        )

    if "7 ngay" in text or "tuan nay" in text or "gan day" in text:
        return TimeRange(
            type="rolling_period",
            start=now - timedelta(days=7),
            end=now,
            period_days=7,
            is_fallback=False
        )

    return TimeRange(
        type="rolling_period",
        start=now - timedelta(days=7),
        end=now,
        period_days=7,
        is_fallback=True
    )
