from __future__ import annotations


def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining_seconds = seconds - minutes * 60
    return f"{minutes:02d}:{remaining_seconds:05.2f}"


def format_optional_time(seconds: float | None) -> str:
    if seconds is None:
        return "--:--.--"
    return format_time(seconds)
