from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cndc_dashboard.dashboard_service import DashboardService
from cndc_extractor.config import Settings
from cndc_extractor.exceptions import CNDCExtractorError
from cndc_extractor.models import JsonData


class FakeClient:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def get_json(self, url: str) -> JsonData:
        self.calls.append(url)
        if self.fail:
            raise CNDCExtractorError("fallo simulado")
        if url.endswith("/fechas"):
            return [{"tipo": "TIEMPO_REAL", "fecha": "2026-06-18"}]
        if "/generacion" in url:
            return [
                {"codigo": "PREV", "valores": [1] * 96},
                {"codigo": "TOT", "valores": [2, None] + [3] * 93 + [-1]},
                {"codigo": "TERMO", "valores": [4] * 96},
                {"codigo": "HIDRO", "valores": [5] * 96},
                {"codigo": "SOLAR", "valores": [6] * 96},
                {"codigo": "EOL", "valores": [7] * 96},
                {"codigo": "BAGAZO", "valores": [8] * 96},
            ]
        if "/demanda" in url:
            return [
                {"codigo": "SANTA CRUZ", "valores": [1] * 96},
                {"codigo": "LA PAZ", "valores": [2] * 96},
                {"codigo": "COCHABAMBA", "valores": [3] * 96},
                {"codigo": "POTOSI", "valores": [4] * 96},
                {"codigo": "ORURO", "valores": [5] * 96},
                {"codigo": "TARIJA", "valores": [6] * 96},
                {"codigo": "CHUQUISACA", "valores": [7] * 96},
                {"codigo": "BENI", "valores": [8] * 96},
                {"codigo": "Prev.SCZ", "valores": [100] * 96},
            ]
        if "/frecuencia" in url:
            return [
                {"valor": 50.058, "hora": "2026-06-18T10:08:55Z"},
                {"valor": 50.4, "hora": "2026-06-18T10:08:56Z"},
            ]
        return []


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        base_url="https://example.test/rt",
        http_timeout_seconds=1,
        http_retries=0,
        frequency_records=360,
        timezone="America/La_Paz",
        raw_data_directory=tmp_path / "raw",
        normalized_data_directory=tmp_path / "normalized",
        logs_directory=tmp_path / "logs",
    )


def test_generation_uses_latest_date_and_produces_96_labels(settings: Settings) -> None:
    service = DashboardService(settings, client=FakeClient())
    payload = service.generation()
    assert payload["fecha"] == "2026-06-18"
    assert len(payload["labels"]) == 96
    assert payload["labels"][-1] == "24:00"
    assert any(value is None for item in payload["series"] if item["nombre"] == "Total" for value in item["valores"])


def test_generation_respects_manual_date(settings: Settings) -> None:
    client = FakeClient()
    service = DashboardService(settings, client=client)
    payload = service.generation("2026-06-17")
    assert payload["fecha"] == "2026-06-17"
    assert any("fecha=2026-06-17" in call for call in client.calls)


def test_demand_has_total_sin_and_no_prev_scz(settings: Settings) -> None:
    service = DashboardService(settings, client=FakeClient())
    payload = service.demand()
    codes = [item["codigo"] for item in payload["series"]]
    assert "TOTAL_SIN" in codes
    assert "Prev.SCZ" not in codes
    assert len(payload["series"]) == 9


def test_frequency_keeps_bolivia_wall_clock(settings: Settings) -> None:
    service = DashboardService(settings, client=FakeClient())
    payload = service.frequency()
    assert payload["timestamps"][0] == "2026-06-18T10:08:55-04:00"
    assert payload["labels"][0] == "10:08:55"
    assert payload["limite_inferior"] == 49.75
    assert payload["nominal"] == 50.0
    assert payload["limite_superior"] == 50.25


def test_invalid_date_fails(settings: Settings) -> None:
    service = DashboardService(settings, client=FakeClient())
    with pytest.raises(CNDCExtractorError):
        service.generation("18-06-2026")


def test_api_failure_uses_memory_cache(settings: Settings) -> None:
    client = FakeClient()
    service = DashboardService(settings, client=client)
    service.frequency()
    cached = service.cache.get("frecuencia:360")
    assert cached is not None
    cached.updated_at = datetime.now().astimezone() - timedelta(seconds=120)
    client.fail = True
    payload = service.frequency()
    assert payload["source"] == "CACHE_MEMORY"
