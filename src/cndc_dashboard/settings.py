"""Dashboard settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from cndc_extractor.config import Settings as ExtractorSettings
from cndc_extractor.exceptions import ConfigurationError


@dataclass(frozen=True)
class DashboardRotationPage:
    id: str
    name: str
    url: str
    enabled: bool = True

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> DashboardRotationPage:
        try:
            page = cls(
                id=str(data["id"]).strip(),
                name=str(data["name"]).strip(),
                url=str(data["url"]).strip(),
                enabled=bool(data.get("enabled", True)),
            )
        except KeyError as exc:
            raise ConfigurationError(f"Pagina de rotacion incompleta: {exc}") from exc
        page.validate()
        return page

    def validate(self) -> None:
        if not self.id:
            raise ConfigurationError("Pagina de rotacion sin id.")
        if not self.name:
            raise ConfigurationError(f"Pagina de rotacion {self.id!r} sin nombre.")
        if not _is_allowed_dashboard_url(self.url):
            raise ConfigurationError(f"URL de rotacion invalida para {self.id!r}: {self.url}")

    def public_payload(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "url": self.url}


@dataclass(frozen=True)
class DashboardRotationSettings:
    enabled: bool
    interval_seconds: int
    show_controls: bool
    auto_hide_controls_seconds: int
    load_timeout_seconds: int
    pages: tuple[DashboardRotationPage, ...]

    @classmethod
    def load(cls, path: Path = Path("config/settings.json")) -> DashboardRotationSettings:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(f"No existe el archivo de configuracion: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Configuracion JSON invalida en {path}: {exc}") from exc
        return cls.from_mapping(data.get("dashboard_rotation", {}))

    @classmethod
    def from_mapping(cls, data: object) -> DashboardRotationSettings:
        if not isinstance(data, dict):
            raise ConfigurationError("La configuracion dashboard_rotation debe ser un objeto.")

        page_items = data.get("pages")
        if not isinstance(page_items, list):
            raise ConfigurationError("dashboard_rotation.pages debe ser una lista.")

        pages = tuple(DashboardRotationPage.from_mapping(item) for item in page_items if isinstance(item, dict))
        if len(pages) != len(page_items):
            raise ConfigurationError("Todas las paginas de dashboard_rotation.pages deben ser objetos.")

        settings = cls(
            enabled=bool(data.get("enabled", True)),
            interval_seconds=int(data.get("interval_seconds", 40)),
            show_controls=bool(data.get("show_controls", True)),
            auto_hide_controls_seconds=int(data.get("auto_hide_controls_seconds", 4)),
            load_timeout_seconds=int(data.get("load_timeout_seconds", 12)),
            pages=pages,
        )
        settings.validate()
        return settings

    @property
    def enabled_pages(self) -> tuple[DashboardRotationPage, ...]:
        return tuple(page for page in self.pages if page.enabled)

    def validate(self) -> None:
        if self.interval_seconds < 1:
            raise ConfigurationError("dashboard_rotation.interval_seconds debe ser mayor a cero.")
        if self.auto_hide_controls_seconds < 1:
            raise ConfigurationError("dashboard_rotation.auto_hide_controls_seconds debe ser mayor a cero.")
        if self.load_timeout_seconds < 1:
            raise ConfigurationError("dashboard_rotation.load_timeout_seconds debe ser mayor a cero.")
        if not self.enabled_pages:
            raise ConfigurationError("dashboard_rotation requiere al menos una pagina habilitada.")

    def public_payload(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "show_controls": self.show_controls,
            "auto_hide_controls_seconds": self.auto_hide_controls_seconds,
            "load_timeout_seconds": self.load_timeout_seconds,
            "pages": [page.public_payload() for page in self.enabled_pages],
        }


@dataclass(frozen=True)
class DashboardSettings:
    host: str = "127.0.0.1"
    port: int = 8000
    frequency_refresh_seconds: int = 60
    generation_refresh_seconds: int = 900
    demand_refresh_seconds: int = 900
    max_frequency_records: int = 3600
    source: str = "API"

    @classmethod
    def from_extractor(cls, extractor: ExtractorSettings) -> DashboardSettings:
        return cls(frequency_refresh_seconds=60, generation_refresh_seconds=900, demand_refresh_seconds=900)


def _is_allowed_dashboard_url(url: str) -> bool:
    if url.startswith("/") and not url.startswith("//"):
        return True

    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
