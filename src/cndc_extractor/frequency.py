"""Frequency normalization."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from dateutil import parser

from .models import Warnings


def parse_cndc_frequency_timestamp(value: str, timezone_name: str = "America/La_Paz") -> datetime:
    """Parse CNDC frequency timestamps.

    The frequency endpoint emits local Bolivia wall-clock timestamps with a trailing
    ``Z``. For this endpoint only, that suffix is misleading and must not trigger
    a UTC-to-Bolivia conversion.
    """
    zone = ZoneInfo(timezone_name)
    text = value.strip()
    if text.endswith("Z"):
        parsed = parser.isoparse(text[:-1])
        return parsed.replace(tzinfo=zone)
    parsed = parser.isoparse(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def normalize_frequency(
    records: list[dict[str, Any]],
    timezone_name: str,
    warnings: Warnings,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    deduped: dict[datetime, dict[str, Any]] = {}
    first_original: str | None = None
    last_original: str | None = None
    for record in records:
        original = record.get("hora")
        value = record.get("valor")
        try:
            original_text = str(original)
            hz = float(value)
            bolivia_dt = parse_cndc_frequency_timestamp(original_text, timezone_name)
        except (TypeError, ValueError) as exc:
            warnings.frequency_invalid_records += 1
            logger.warning("Registro de frecuencia invalido omitido: %s (%s)", record, exc)
            continue

        first_original = first_original or original_text
        last_original = original_text
        if original_text.strip().endswith("Z"):
            warnings.frequency_z_timestamps += 1
            warnings.frequency_timestamp_notes.add(
                "timestamps terminados en Z del endpoint de frecuencia interpretados como hora local de Bolivia sin desplazamiento"
            )
        elif parser.isoparse(original_text).tzinfo is None:
            warnings.frequency_naive_timestamps += 1
            warnings.frequency_timestamp_notes.add(
                "timestamps ingenuos interpretados como America/La_Paz sin desplazamiento"
            )
        else:
            warnings.frequency_offset_timestamps += 1
            warnings.frequency_timestamp_notes.add(
                "timestamps con offset explicito convertidos a America/La_Paz"
            )
        deduped[bolivia_dt] = {
            "fecha_hora_original": original_text,
            "fecha_hora_bolivia": bolivia_dt.isoformat(),
            "fecha": bolivia_dt.strftime("%d/%m/%Y"),
            "hora": bolivia_dt.strftime("%H:%M:%S"),
            "hz": hz,
            "estado_rango": "Normal" if 49.75 <= hz <= 50.25 else "Fuera de rango",
        }
    rows = [deduped[key] for key in sorted(deduped)]
    logger.info(
        "Frecuencia timestamps: z=%s ingenuos=%s offset=%s estrategia=wall_clock_bolivia_with_misleading_z primero=%s ultimo=%s primera_normalizada=%s ultima_normalizada=%s",
        warnings.frequency_z_timestamps,
        warnings.frequency_naive_timestamps,
        warnings.frequency_offset_timestamps,
        first_original,
        last_original,
        rows[0]["fecha_hora_bolivia"] if rows else None,
        rows[-1]["fecha_hora_bolivia"] if rows else None,
    )
    return rows
