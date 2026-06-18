"""Validation summary generation."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from .models import Warnings


def count_with_data(rows: list[dict[str, Any]], series_key: str = "serie", value_key: str = "mw") -> Counter:
    counter: Counter = Counter()
    for row in rows:
        if row.get(value_key) is not None:
            counter[str(row.get(series_key))] += 1
    return counter


def build_validation_summary(
    operation_date: date,
    selection_mode: str,
    read_mode: str,
    generation_rows: list[dict[str, Any]],
    demand_rows: list[dict[str, Any]],
    frequency_rows: list[dict[str, Any]],
    frequency_downloaded: int,
    warnings: Warnings,
) -> str:
    gen_counts = count_with_data(generation_rows)
    dem_counts = count_with_data(demand_rows)
    gen_series = list(dict.fromkeys(str(row["serie"]) for row in generation_rows))
    dem_series = list(dict.fromkeys(str(row["serie"]) for row in demand_rows))
    hz_values = [float(row["hz"]) for row in frequency_rows]
    last_reading = frequency_rows[-1]["fecha_hora_bolivia"] if frequency_rows else "Sin datos"
    lines = [
        "PRUEBA DE EXTRACCIÓN CNDC - FASE 1",
        "",
        f"Fecha seleccionada automaticamente: {operation_date.isoformat()}",
        f"Modo de seleccion: {selection_mode}",
        f"Modo de lectura: {read_mode}",
        "",
        "GENERACION",
    ]
    for series in gen_series:
        lines.append(f"{series}: 96 intervalos, {gen_counts[series]} con dato, {96 - gen_counts[series]} vacios")
    lines.extend(["", "DEMANDA"])
    for series in dem_series:
        lines.append(f"{series}: 96 intervalos, {dem_counts[series]} con dato, {96 - dem_counts[series]} vacios")
    lines.extend(
        [
            "",
            "FRECUENCIA",
            f"Registros descargados: {frequency_downloaded}",
            f"Registros normalizados: {len(frequency_rows)}",
            f"Valor minimo: {min(hz_values) if hz_values else 'Sin datos'}",
            f"Valor maximo: {max(hz_values) if hz_values else 'Sin datos'}",
            f"Ultima lectura: {last_reading}",
            "",
            "ADVERTENCIAS",
            "Series desconocidas: "
            + (", ".join(sorted(warnings.unknown_generation_codes)) or "Ninguna"),
            "Series faltantes: " + (", ".join(sorted(warnings.missing_demand_codes)) or "Ninguna"),
            "Registros de frecuencia invalidos: " + str(warnings.frequency_invalid_records),
            "Interpretacion timestamps frecuencia: "
            + (
                "Los timestamps terminados en Z del endpoint de frecuencia del CNDC "
                "fueron interpretados como hora local de Bolivia sin desplazamiento "
                "del reloj, debido al comportamiento observado de la fuente."
                if warnings.frequency_z_timestamps
                else (", ".join(sorted(warnings.frequency_timestamp_notes)) or "Sin registros")
            ),
        ]
    )
    return "\n".join(lines) + "\n"
