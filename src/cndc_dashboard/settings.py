"""Dashboard settings."""

from __future__ import annotations

from dataclasses import dataclass

from cndc_extractor.config import Settings as ExtractorSettings


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
