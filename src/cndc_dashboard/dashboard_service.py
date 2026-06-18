"""Data service for the local dashboard."""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, cast

from cndc_extractor.config import Settings
from cndc_extractor.date_selector import parse_operation_date, select_latest_realtime_date
from cndc_extractor.demand import normalize_demand
from cndc_extractor.exceptions import CNDCExtractorError
from cndc_extractor.frequency import normalize_frequency
from cndc_extractor.generation import normalize_generation
from cndc_extractor.http_client import HTTPJsonClient
from cndc_extractor.models import JsonData, Warnings
from cndc_extractor.storage import bolivia_now_iso

from .cache import MemoryCache


class JsonClient(Protocol):
    def get_json(self, url: str) -> JsonData:
        """Return JSON data."""


class DashboardService:
    def __init__(
        self,
        extractor_settings: Settings,
        cache: MemoryCache | None = None,
        client: JsonClient | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = extractor_settings
        self.cache = cache or MemoryCache()
        self.logger = logger or logging.getLogger("cndc_extractor")
        self.client = client or HTTPJsonClient(
            extractor_settings.http_timeout_seconds,
            extractor_settings.http_retries,
            self.logger,
        )

    def status(self) -> dict[str, Any]:
        latest = self.latest_date()
        return {
            "status": "ok",
            "source": latest["source"],
            "latest_date": latest["fecha"],
            "timezone": self.settings.timezone,
            "last_update": bolivia_now_iso(self.settings.timezone),
        }

    def latest_date(self) -> dict[str, Any]:
        entry = self.cache.get_or_load("fechas:latest", 300, self._load_latest_date)
        payload = dict(entry.value)
        payload["source"] = entry.source
        return payload

    def generation(self, fecha: str | None = None) -> dict[str, Any]:
        operation_date = self._resolve_date(fecha)
        key = f"generacion:{operation_date.isoformat()}"
        ttl = 900 if operation_date == self._resolve_date(None) else 86400
        return self._cached_with_fallback(key, ttl, lambda: self._load_generation(operation_date), "generation")

    def demand(self, fecha: str | None = None) -> dict[str, Any]:
        operation_date = self._resolve_date(fecha)
        key = f"demanda:{operation_date.isoformat()}"
        ttl = 900 if operation_date == self._resolve_date(None) else 86400
        return self._cached_with_fallback(key, ttl, lambda: self._load_demand(operation_date), "demand")

    def frequency(self, registros: int = 360) -> dict[str, Any]:
        if registros < 1 or registros > 3600:
            raise CNDCExtractorError("registros debe estar entre 1 y 3600")
        key = f"frecuencia:{registros}"
        return self._cached_with_fallback(key, 60, lambda: self._load_frequency(registros), "frequency")

    def refresh(self) -> dict[str, str]:
        self.cache.invalidate()
        return {"status": "ok", "message": "cache invalidada"}

    def _cached_with_fallback(
        self, key: str, ttl_seconds: int, loader: Any, disk_kind: str
    ) -> dict[str, Any]:
        try:
            entry = self.cache.get_or_load(key, ttl_seconds, loader)
            payload = dict(entry.value)
            payload["source"] = entry.source
            return payload
        except Exception as exc:
            self.logger.exception("Fallo API para %s; intentando cache o disco", key)
            cached = self.cache.get(key)
            if cached is not None:
                payload = dict(cached.value)
                payload["source"] = "CACHE_MEMORY"
                payload.setdefault("warnings", []).append(f"API no disponible: {exc}")
                return payload
            disk = self._load_disk_fallback(disk_kind)
            if disk is not None:
                disk["source"] = "CACHE_DISK"
                disk.setdefault("warnings", []).append(f"API no disponible: {exc}")
                return disk
            raise CNDCExtractorError(f"No se pudo obtener {disk_kind}: {exc}") from exc

    def _load_latest_date(self) -> dict[str, Any]:
        records = self._fetch_list(f"{self.settings.base_url}/fechas", "fechas")
        selection = select_latest_realtime_date(records)
        return {
            "fecha": selection.operation_date.isoformat(),
            "tipo": "TIEMPO_REAL" if selection.mode == "TIEMPO_REAL" else "RESPALDO",
            "modo_seleccion": selection.mode,
        }

    def _load_generation(self, operation_date: date) -> dict[str, Any]:
        previous_date = operation_date - timedelta(days=1)
        seven_days_date = operation_date - timedelta(days=7)
        current = self._fetch_list(
            f"{self.settings.base_url}/generacion?fecha={operation_date.isoformat()}",
            "generacion actual",
        )
        previous = self._fetch_list(
            f"{self.settings.base_url}/generacion?fecha={previous_date.isoformat()}",
            "generacion ayer",
        )
        seven = self._fetch_list(
            f"{self.settings.base_url}/generacion?fecha={seven_days_date.isoformat()}",
            "generacion hace siete dias",
        )
        warnings = Warnings()
        rows = normalize_generation(operation_date, current, previous, seven, warnings, self.logger)
        return _rows_to_series_payload(operation_date, "MW", rows, "mw", warnings)

    def _load_demand(self, operation_date: date) -> dict[str, Any]:
        records = self._fetch_list(
            f"{self.settings.base_url}/demanda?fecha={operation_date.isoformat()}",
            "demanda",
        )
        warnings = Warnings()
        rows = normalize_demand(operation_date, records, warnings, self.logger)
        payload = _rows_to_series_payload(operation_date, "MW", rows, "mw", warnings)
        order = ["TOTAL_SIN", "SANTA CRUZ", "LA PAZ", "COCHABAMBA", "POTOSI", "ORURO", "TARIJA", "CHUQUISACA", "BENI"]
        payload["series"].sort(key=lambda item: order.index(item["codigo"]) if item["codigo"] in order else 99)
        return payload

    def _load_frequency(self, registros: int) -> dict[str, Any]:
        records = self._fetch_list(
            f"{self.settings.base_url}/frecuencia/historial?registros={registros}",
            "frecuencia",
        )
        warnings = Warnings()
        rows = normalize_frequency(records, self.settings.timezone, warnings, self.logger)
        values = [row["hz"] for row in rows]
        labels = [row["hora"] for row in rows]
        timestamps = [row["fecha_hora_bolivia"] for row in rows]
        last = rows[-1] if rows else {}
        return {
            "unidad": "Hz",
            "timezone": self.settings.timezone,
            "labels": labels,
            "timestamps": timestamps,
            "valores": values,
            "ultimo_valor": last.get("hz"),
            "ultima_hora": last.get("hora"),
            "estado": last.get("estado_rango"),
            "limite_inferior": 49.75,
            "nominal": 50.0,
            "limite_superior": 50.25,
            "actualizado_en": bolivia_now_iso(self.settings.timezone),
            "warnings": _warning_list(warnings),
        }

    def _resolve_date(self, fecha: str | None) -> date:
        if fecha:
            parsed = parse_operation_date(fecha)
            if parsed is None or parsed.isoformat() != fecha:
                raise CNDCExtractorError("fecha debe usar formato YYYY-MM-DD")
            return parsed
        return date.fromisoformat(str(self.latest_date()["fecha"]))

    def _fetch_list(self, url: str, name: str) -> list[dict[str, Any]]:
        started = datetime.now()
        data = self.client.get_json(url)
        elapsed = (datetime.now() - started).total_seconds()
        if not isinstance(data, list):
            raise CNDCExtractorError(f"La respuesta de {name} no es una lista")
        rows = [item for item in data if isinstance(item, dict)]
        self.logger.info("%s: %s registros en %.2fs", name, len(rows), elapsed)
        if len(rows) != len(data):
            raise CNDCExtractorError(f"La respuesta de {name} contiene elementos invalidos")
        return cast(list[dict[str, Any]], rows)

    def _load_disk_fallback(self, kind: str) -> dict[str, Any] | None:
        normalized_root = self.settings.normalized_data_directory
        if not normalized_root.exists():
            return None
        dated_dirs = sorted([item for item in normalized_root.iterdir() if item.is_dir()], reverse=True)
        for folder in dated_dirs:
            try:
                operation_date = date.fromisoformat(folder.name)
            except ValueError:
                continue
            if kind == "generation":
                rows = _read_csv(folder / "generacion_normalizada.csv")
                if rows:
                    return _csv_rows_to_series_payload(operation_date, "MW", rows, "mw")
            if kind == "demand":
                rows = _read_csv(folder / "demanda_normalizada.csv")
                if rows:
                    return _csv_rows_to_series_payload(operation_date, "MW", rows, "mw")
            if kind == "frequency":
                rows = _read_csv(folder / "frecuencia_normalizada.csv")
                if rows:
                    return _csv_frequency_payload(rows, self.settings.timezone)
        return None


def _rows_to_series_payload(
    operation_date: date,
    unit: str,
    rows: list[dict[str, Any]],
    value_key: str,
    warnings: Warnings,
) -> dict[str, Any]:
    labels = [row["hora"] for row in rows if row["serie"] == rows[0]["serie"]] if rows else []
    series = []
    for name in dict.fromkeys(row["serie"] for row in rows):
        selected = [row for row in rows if row["serie"] == name]
        series.append(
            {
                "codigo": selected[0]["codigo"],
                "nombre": name,
                "valores": [row[value_key] for row in selected],
            }
        )
    return {
        "fecha": operation_date.isoformat(),
        "unidad": unit,
        "labels": labels,
        "series": series,
        "actualizado_en": bolivia_now_iso("America/La_Paz"),
        "warnings": _warning_list(warnings),
    }


def _csv_rows_to_series_payload(
    operation_date: date, unit: str, rows: list[dict[str, str]], value_key: str
) -> dict[str, Any]:
    labels = [row["hora"] for row in rows if row["serie"] == rows[0]["serie"]] if rows else []
    series = []
    for name in dict.fromkeys(row["serie"] for row in rows):
        selected = [row for row in rows if row["serie"] == name]
        series.append(
            {
                "codigo": selected[0]["codigo"],
                "nombre": name,
                "valores": [_float_or_none(row.get(value_key, "")) for row in selected],
            }
        )
    return {
        "fecha": operation_date.isoformat(),
        "unidad": unit,
        "labels": labels,
        "series": series,
        "actualizado_en": bolivia_now_iso("America/La_Paz"),
        "warnings": [],
    }


def _csv_frequency_payload(rows: list[dict[str, str]], timezone: str) -> dict[str, Any]:
    values = [_float_or_none(row.get("hz", "")) for row in rows]
    return {
        "unidad": "Hz",
        "timezone": timezone,
        "labels": [row["hora"] for row in rows],
        "timestamps": [row["fecha_hora_bolivia"] for row in rows],
        "valores": values,
        "ultimo_valor": values[-1] if values else None,
        "ultima_hora": rows[-1]["hora"] if rows else None,
        "estado": rows[-1]["estado_rango"] if rows else None,
        "limite_inferior": 49.75,
        "nominal": 50.0,
        "limite_superior": 50.25,
        "actualizado_en": bolivia_now_iso(timezone),
        "warnings": [],
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _float_or_none(value: Any) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def _warning_list(warnings: Warnings) -> list[str]:
    items = []
    if warnings.unknown_generation_codes:
        items.append("Series desconocidas: " + ", ".join(sorted(warnings.unknown_generation_codes)))
    if warnings.missing_demand_codes:
        items.append("Series faltantes: " + ", ".join(sorted(warnings.missing_demand_codes)))
    if warnings.frequency_invalid_records:
        items.append(f"Registros de frecuencia invalidos: {warnings.frequency_invalid_records}")
    return items
