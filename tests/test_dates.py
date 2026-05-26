from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from data_extraction.utils.dates import backfill_window, previous_day_window


def test_previous_day_window() -> None:
    run_time = datetime(2026, 5, 26, 9, 30, tzinfo=ZoneInfo("Europe/Malta"))

    window = previous_day_window(run_time)

    assert window.start.isoformat() == "2026-05-25T00:00:00+02:00"
    assert window.end.isoformat() == "2026-05-26T00:00:00+02:00"


def test_previous_day_window_accepts_naive_datetime() -> None:
    run_time = datetime(2026, 5, 26, 9, 30)

    window = previous_day_window(run_time)

    assert window.start.date().isoformat() == "2026-05-25"
    assert window.end.date().isoformat() == "2026-05-26"


def test_backfill_window() -> None:
    run_time = datetime(2026, 5, 26, 9, 30, tzinfo=ZoneInfo("Europe/Malta"))

    window = backfill_window(run_time, years=2)

    assert window.end.isoformat() == "2026-05-26T00:00:00+02:00"
    assert (window.end - window.start).days == 730


def test_backfill_years_must_be_positive() -> None:
    with pytest.raises(ValueError):
        backfill_window(years=0)