"""FastAPI application factory."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cndc_extractor.config import Settings
from cndc_extractor.logging_config import configure_logging

from .dashboard_service import DashboardService
from .plotly_vendor import ensure_plotly_vendor
from .routes import router
from .settings import DashboardRotationSettings


def create_app(service: DashboardService | None = None) -> FastAPI:
    package_dir = Path(__file__).resolve().parent
    static_dir = package_dir / "static"
    settings = Settings.load()
    logger = configure_logging(settings.logs_directory)
    ensure_plotly_vendor(static_dir, logger)

    app = FastAPI(title="Dashboard CNDC local", version="0.2.0")
    app.state.logger = logger
    app.state.extractor_settings = settings
    app.state.dashboard_service = service or DashboardService(settings, logger=logger)
    app.state.dashboard_rotation = DashboardRotationSettings.load()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    def _startup() -> None:
        logging.getLogger("cndc_extractor").info("Dashboard CNDC iniciado")

    @app.on_event("shutdown")
    def _shutdown() -> None:
        logging.getLogger("cndc_extractor").info("Dashboard CNDC detenido")

    return app


app = create_app()
