"""Generation normalization."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from .models import Warnings
from .normalizers import clean_number, interval_datetime, interval_hour, values_for

GENERATION_LABELS = {
    "PREV": "Previsto",
    "TOT": "Total",
    "TERMO": "Termoeléctrica",
    "HIDRO": "Hidroeléctrica",
    "SOLAR": "Solar",
    "EOL": "Eólica",
    "BAGAZO": "Renovable",
}
VISIBLE_CODES = set(GENERATION_LABELS)
EXCLUDED_CODES = {"RENO"}


def normalize_generation(
    operation_date: date,
    current: list[dict[str, Any]],
    previous_day: list[dict[str, Any]],
    seven_days: list[dict[str, Any]],
    warnings: Warnings,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    detected = {str(item.get("codigo", "")).strip() for item in current}
    unknown = {code for code in detected if code and code not in VISIBLE_CODES and code not in EXCLUDED_CODES}
    warnings.unknown_generation_codes.update(unknown)
    if unknown:
        logger.warning("Series de generacion desconocidas: %s", ", ".join(sorted(unknown)))
    logger.info("Series de generacion detectadas: %s", ", ".join(sorted(detected)))

    for record in current:
        code = str(record.get("codigo", "")).strip()
        if code in EXCLUDED_CODES:
            continue
        label = GENERATION_LABELS.get(code, code)
        rows.extend(_series_rows(operation_date, code, label, "Actual", values_for(record)))

    for label, data in (("Total Ayer", previous_day), ("Total Hace 7 días", seven_days)):
        total_record = next((item for item in data if str(item.get("codigo", "")).strip() == "TOT"), None)
        if total_record is not None:
            rows.extend(_series_rows(operation_date, "TOT", label, label, values_for(total_record)))
    return rows


def _series_rows(
    operation_date: date,
    code: str,
    label: str,
    comparison: str,
    values: list[Any],
) -> list[dict[str, Any]]:
    rows = []
    for index in range(96):
        interval = index + 1
        rows.append(
            {
                "fecha_operacion": operation_date.isoformat(),
                "intervalo": interval,
                "hora": interval_hour(interval),
                "fecha_hora": interval_datetime(operation_date, interval).isoformat(sep=" "),
                "codigo": code,
                "serie": label,
                "comparacion": comparison,
                "mw": clean_number(values[index]) if index < len(values) else None,
            }
        )
    return rows
