from datetime import datetime, timedelta, timezone

from utils.time_formatter import format_relative_time


def test_format_relative_time_returns_just_now_for_less_than_one_minute():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(seconds=30)).isoformat()

    assert format_relative_time(timestamp, now=now) == "just now"


def test_format_relative_time_returns_one_minute_ago():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(minutes=1)).isoformat()

    assert format_relative_time(timestamp, now=now) == "1 minute ago"


def test_format_relative_time_returns_multiple_minutes_ago():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(minutes=4)).isoformat()

    assert format_relative_time(timestamp, now=now) == "4 minutes ago"


def test_format_relative_time_returns_one_hour_ago():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(hours=1)).isoformat()

    assert format_relative_time(timestamp, now=now) == "1 hour ago"


def test_format_relative_time_returns_multiple_hours_ago():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(hours=3)).isoformat()

    assert format_relative_time(timestamp, now=now) == "3 hours ago"


def test_format_relative_time_returns_one_day_ago():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(days=1)).isoformat()

    assert format_relative_time(timestamp, now=now) == "1 day ago"


def test_format_relative_time_returns_multiple_days_ago():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    timestamp = (now - timedelta(days=5)).isoformat()

    assert format_relative_time(timestamp, now=now) == "5 days ago"


def test_format_relative_time_returns_unknown_for_invalid_timestamp():
    assert format_relative_time("not a timestamp") == "unknown"


def test_format_relative_time_returns_unknown_for_empty_timestamp():
    assert format_relative_time("") == "unknown"
