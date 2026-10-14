from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def shanghai_today(now_utc: datetime) -> date:
    return as_utc(now_utc).astimezone(SHANGHAI).date()


def to_shanghai_iso(stamp: str) -> str:
    parsed = datetime.fromisoformat(stamp)
    return as_utc(parsed).astimezone(SHANGHAI).isoformat(timespec="seconds")


def shift_iso_date(day: date, days: int) -> str:
    return (day + timedelta(days=days)).isoformat()
