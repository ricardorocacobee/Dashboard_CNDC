"""Demand normalization."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from .models import Warnings
from .normalizers import clean_number, interval_datetime, interval_hour, values_for

DEMAND_LABELS = {
    "SANTA CRUZ": "Santa Cruz",
    "LA PAZ": "La Paz",
    "COCHABAMBA": "Cochabamba",
    "POTOSI": "Potosí",
    "ORURO": "Oruro",
    "TARIJA": "Tarija",
    "CHUQUISACA": "Chuquisaca",
    "BENI": "Beni",
}
EXCLUDED_DEMAND = {"Prev.SCZ"}


def normalize_demand(
    operation_date: date,
    records: list[dict[str, Any]],
    warnings: Warnings,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    by_code = {str(item.get("codigo", "")).strip(): item for item in records}
    detected = set(by_code) - EXCLUDED_DEMAND
    missing = set(DEMAND_LABELS) - detected
    warnings.missing_demand_codes.update(missing)
    if missing:
        logger.warning("Series de demanda faltantes: %s", ", ".join(sorted(missing)))
    logger.info("Series de demanda detectadas: %s", ", ".join(sorted(set(by_code))))

    rows: list[dict[str, Any]] = []
    clean_values_by_code: dict[str, list[float | None]] = {}
    for code, label in DEMAND_LABELS.items():
        values = values_for(by_code.get(code, {}))
        clean_values = [clean_number(values[index]) if index < len(values) else None for index in range(96)]
        clean_values_by_code[code] = clean_values
        for index, mw in enumerate(clean_values, start=1):
            rows.append(_row(operation_date, index, code, label, mw))

    for interval_index in range(96):
        values = [series[interval_index] for series in clean_values_by_code.values()]
        numeric = [value for value in values if value is not None]
        total = sum(numeric) if numeric else None
        rows.append(_row(operation_date, interval_index + 1, "TOTAL_SIN", "Total SIN", total))
    return rows


def _row(operation_date: date, interval: int, code: str, label: str, mw: float | None) -> dict[str, Any]:
    return {
        "fecha_operacion": operation_date.isoformat(),
        "intervalo": interval,
        "hora": interval_hour(interval),
        "fecha_hora": interval_datetime(operation_date, interval).isoformat(sep=" "),
        "codigo": code,
        "serie": label,
        "mw": mw,
    }
