from datetime import datetime, timezone


def format_relative_time(iso_timestamp, now=None):
    if not iso_timestamp:
        return "unknown"

    try:
        timestamp = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return "unknown"

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = max(0, int((current_time - timestamp).total_seconds()))

    if elapsed_seconds < 60:
        return "just now"

    elapsed_minutes = elapsed_seconds // 60
    if elapsed_minutes < 60:
        if elapsed_minutes == 1:
            return "1 minute ago"
        return f"{elapsed_minutes} minutes ago"

    elapsed_hours = elapsed_minutes // 60
    if elapsed_hours < 24:
        if elapsed_hours == 1:
            return "1 hour ago"
        return f"{elapsed_hours} hours ago"

    elapsed_days = elapsed_hours // 24
    if elapsed_days == 1:
        return "1 day ago"
    return f"{elapsed_days} days ago"
