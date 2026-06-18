"""Shared normalizing helpers."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any


def interval_hour(interval: int) -> str:
    if interval < 1 or interval > 96:
        raise ValueError("intervalo fuera de rango 1..96")
    total_minutes = interval * 15
    if total_minutes == 1440:
        return "24:00"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def interval_datetime(operation_date: date, interval: int) -> datetime:
    return datetime.combine(operation_date, time.min) + timedelta(minutes=interval * 15)


def clean_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number == -1:
        return None
    return number


def values_for(record: dict[str, Any]) -> list[Any]:
    values = record.get("valores", [])
    return values if isinstance(values, list) else []
