"""Dashboard routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from cndc_extractor.exceptions import CNDCExtractorError

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")


def service_for(request: Request):
    return request.app.state.dashboard_service


@router.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse("/generacion.html", status_code=307)


@router.get("/generacion.html", response_class=HTMLResponse)
def generation_page(request: Request):
    return templates.TemplateResponse(request, "generacion.html")


@router.get("/demanda.html", response_class=HTMLResponse)
def demand_page(request: Request):
    return templates.TemplateResponse(request, "demanda.html")


@router.get("/frecuencia.html", response_class=HTMLResponse)
def frequency_page(request: Request):
    return templates.TemplateResponse(request, "frecuencia.html")


@router.get("/api/status")
def status(request: Request):
    return service_for(request).status()


@router.get("/api/fechas/latest")
def latest_date(request: Request):
    return service_for(request).latest_date()


@router.get("/api/generacion")
def generation(request: Request, fecha: str | None = None):
    try:
        return service_for(request).generation(fecha)
    except CNDCExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/demanda")
def demand(request: Request, fecha: str | None = None):
    try:
        return service_for(request).demand(fecha)
    except CNDCExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/frecuencia")
def frequency(request: Request, registros: int = Query(default=360, ge=1, le=3600)):
    try:
        return service_for(request).frequency(registros)
    except CNDCExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/refresh")
def refresh(request: Request):
    return service_for(request).refresh()
