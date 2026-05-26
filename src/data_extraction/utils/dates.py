from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class DateWindow:
    start: datetime
    end: datetime

    def as_dates(self) -> tuple[date, date]:
        return self.start.date(), self.end.date()


def previous_day_window(
    run_datetime: datetime | None = None,
    timezone: str = "Europe/Malta",
) -> DateWindow:
    """
    Returns the previous calendar day window.

    Example:
    If run time is 2026-05-26 09:00 Europe/Malta,
    window is:
      start = 2026-05-25 00:00:00
      end   = 2026-05-26 00:00:00

    End is exclusive.
    """
    tz = ZoneInfo(timezone)

    if run_datetime is None:
        run_datetime = datetime.now(tz)
    elif run_datetime.tzinfo is None:
        run_datetime = run_datetime.replace(tzinfo=tz)
    else:
        run_datetime = run_datetime.astimezone(tz)

    today = run_datetime.date()
    previous_day = today - timedelta(days=1)

    start = datetime.combine(previous_day, time.min, tzinfo=tz)
    end = datetime.combine(today, time.min, tzinfo=tz)

    return DateWindow(start=start, end=end)


def backfill_window(
    run_datetime: datetime | None = None,
    years: int = 2,
    timezone: str = "Europe/Malta",
) -> DateWindow:
    """
    Returns a simple backfill window going back N*365 days from today's midnight.

    For this project, the initial backfill is 2 years.
    End is exclusive.
    """
    if years <= 0:
        raise ValueError("years must be greater than zero")

    tz = ZoneInfo(timezone)

    if run_datetime is None:
        run_datetime = datetime.now(tz)
    elif run_datetime.tzinfo is None:
        run_datetime = run_datetime.replace(tzinfo=tz)
    else:
        run_datetime = run_datetime.astimezone(tz)

    today = run_datetime.date()
    end = datetime.combine(today, time.min, tzinfo=tz)
    start = end - timedelta(days=years * 365)

    return DateWindow(start=start, end=end)