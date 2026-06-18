"""Configuration loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .exceptions import ConfigurationError


@dataclass(frozen=True)
class Settings:
    base_url: str
    http_timeout_seconds: float
    http_retries: int
    frequency_records: int
    timezone: str
    raw_data_directory: Path
    normalized_data_directory: Path
    logs_directory: Path

    @classmethod
    def load(cls, path: Path = Path("config/settings.json"), output_base: Path | None = None) -> Settings:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(f"No existe el archivo de configuracion: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Configuracion JSON invalida en {path}: {exc}") from exc

        base = output_base or Path(".")
        try:
            return cls(
                base_url=str(data["base_url"]).rstrip("/"),
                http_timeout_seconds=float(data.get("http_timeout_seconds", 30)),
                http_retries=int(data.get("http_retries", 3)),
                frequency_records=int(data.get("frequency_records", 360)),
                timezone=str(data.get("timezone", "America/La_Paz")),
                raw_data_directory=base / str(data.get("raw_data_directory", "data/raw")),
                normalized_data_directory=base
                / str(data.get("normalized_data_directory", "data/normalized")),
                logs_directory=base / str(data.get("logs_directory", "logs")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"Configuracion incompleta o invalida: {exc}") from exc
