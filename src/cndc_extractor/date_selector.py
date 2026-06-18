"""Operation date selection."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .exceptions import DateSelectionError
from .models import DateSelection


def parse_operation_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def select_latest_realtime_date(records: list[dict[str, Any]]) -> DateSelection:
    valid: list[tuple[str, date]] = []
    for record in records:
        parsed = parse_operation_date(record.get("fecha"))
        if parsed is not None:
            valid.append((str(record.get("tipo", "")).strip().upper(), parsed))
    if not valid:
        raise DateSelectionError("No existe ninguna fecha valida en la respuesta de /fechas")

    realtime_dates = [item_date for item_type, item_date in valid if item_type == "TIEMPO_REAL"]
    if realtime_dates:
        return DateSelection(max(realtime_dates), "TIEMPO_REAL")
    return DateSelection(max(item_date for _, item_date in valid), "RESPALDO")
