from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cndc_dashboard.app import create_app


class FakeService:
    def status(self):
        return {
            "status": "ok",
            "source": "API",
            "latest_date": "2026-06-18",
            "timezone": "America/La_Paz",
            "last_update": "2026-06-18T10:30:00-04:00",
        }

    def latest_date(self):
        return {"fecha": "2026-06-18", "tipo": "TIEMPO_REAL", "modo_seleccion": "TIEMPO_REAL", "source": "API"}

    def generation(self, fecha=None):
        return {
            "fecha": fecha or "2026-06-18",
            "unidad": "MW",
            "labels": ["00:15", "24:00"],
            "series": [{"codigo": "TOT", "nombre": "Total", "valores": [1, None]}],
            "actualizado_en": "2026-06-18T10:30:00-04:00",
            "source": "API",
            "warnings": [],
        }

    def demand(self, fecha=None):
        return {
            "fecha": fecha or "2026-06-18",
            "unidad": "MW",
            "labels": ["00:15"],
            "series": [{"codigo": "TOTAL_SIN", "nombre": "Total SIN", "valores": [10]}],
            "actualizado_en": "2026-06-18T10:30:00-04:00",
            "source": "API",
            "warnings": [],
        }

    def frequency(self, registros=360):
        return {
            "unidad": "Hz",
            "timezone": "America/La_Paz",
            "labels": ["10:08:55"],
            "timestamps": ["2026-06-18T10:08:55-04:00"],
            "valores": [50.058],
            "ultimo_valor": 50.058,
            "ultima_hora": "10:08:55",
            "limite_inferior": 49.75,
            "nominal": 50.0,
            "limite_superior": 50.25,
            "actualizado_en": "2026-06-18T10:30:00-04:00",
            "source": "API",
            "warnings": [],
        }

    def refresh(self):
        return {"status": "ok"}


def client() -> TestClient:
    return TestClient(create_app(FakeService()))


def test_status_and_latest_date() -> None:
    test_client = client()
    assert test_client.get("/api/status").status_code == 200
    latest = test_client.get("/api/fechas/latest").json()
    assert latest["fecha"] == "2026-06-18"


def test_api_generation_demand_frequency() -> None:
    test_client = client()
    assert test_client.get("/api/generacion").json()["fecha"] == "2026-06-18"
    assert test_client.get("/api/generacion?fecha=2026-06-17").json()["fecha"] == "2026-06-17"
    demand = test_client.get("/api/demanda").json()
    assert demand["series"][0]["codigo"] == "TOTAL_SIN"
    frequency = test_client.get("/api/frecuencia").json()
    assert frequency["timestamps"][0] == "2026-06-18T10:08:55-04:00"
    assert frequency["limite_superior"] == 50.25


def test_root_redirects_to_generation_page() -> None:
    response = client().get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/generacion.html"


def test_three_independent_pages() -> None:
    test_client = client()
    pages = {
        "/generacion.html": ("GENERACIÓN HORARIA", "generacion.js", True),
        "/demanda.html": ("DEMANDA POR DEPARTAMENTO", "demanda.js", True),
        "/frecuencia.html": ("FRECUENCIA DEL SIN", "frecuencia.js", False),
    }
    for path, (title, script, has_date) in pages.items():
        response = test_client.get(path)
        assert response.status_code == 200
        html = response.text
        assert title in html
        assert "Actualizar ahora" in html
        assert "/static/vendor/plotly.min.js" in html
        assert "/static/css/fullscreen-dashboard.css" in html
        assert "/static/js/common.js" in html
        assert f"/static/js/{script}" in html
        assert "cdn" not in html.lower()
        assert 'class="tabs"' not in html
        assert "data-tab" not in html
        assert "Operación en Tiempo Real" not in html
        assert "technicalMetadata" in html
        assert "FUENTE: CNDC" in html
        assert ("type=\"date\"" in html) is has_date


def test_static_assets_exist_and_are_local() -> None:
    test_client = client()
    for path in [
        "/static/css/fullscreen-dashboard.css",
        "/static/js/common.js",
        "/static/js/generacion.js",
        "/static/js/demanda.js",
        "/static/js/frecuencia.js",
        "/static/vendor/plotly.min.js",
    ]:
        response = test_client.get(path)
        assert response.status_code == 200


def test_css_uses_flexible_layout_and_plain_metadata() -> None:
    css = Path("src/cndc_dashboard/static/css/fullscreen-dashboard.css").read_text(encoding="utf-8")
    assert "display: grid" in css
    assert "minmax(0, 1fr)" in css
    assert ".technical-metadata" in css
    metadata_block = css.split(".technical-metadata", 1)[1].split("}", 1)[0]
    assert "background: transparent" in metadata_block
    assert "border: none" in metadata_block
    assert "box-shadow: none" in metadata_block
    assert "font-size: 8px" in metadata_block
    assert "max-width: 600px" not in css
    assert "width: 40%" not in css
    assert "height: 300px" not in css


def test_scripts_are_independent_and_keep_nulls() -> None:
    common = Path("src/cndc_dashboard/static/js/common.js").read_text(encoding="utf-8")
    generation = Path("src/cndc_dashboard/static/js/generacion.js").read_text(encoding="utf-8")
    demand = Path("src/cndc_dashboard/static/js/demanda.js").read_text(encoding="utf-8")
    frequency = Path("src/cndc_dashboard/static/js/frecuencia.js").read_text(encoding="utf-8")
    assert "PLOT_CONFIG" in common
    assert "Plotly.react" in common
    assert "/api/generacion" in generation
    assert "/api/demanda" in demand
    assert "/api/frecuencia" in frequency
    assert "connectgaps: false" in generation
    assert "connectgaps: false" in demand
    assert "|| 0" not in generation
    assert "|| 0" not in demand
    assert ".map((value) => value || 0)" not in generation
    assert ".map((value) => value || 0)" not in demand
