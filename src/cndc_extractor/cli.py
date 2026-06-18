"""Command line interface and orchestration."""

from __future__ import annotations

import argparse
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any, Protocol, cast

from .config import Settings
from .date_selector import parse_operation_date, select_latest_realtime_date
from .demand import normalize_demand
from .exceptions import CNDCExtractorError
from .frequency import normalize_frequency
from .generation import normalize_generation
from .har_client import HARJsonClient
from .http_client import HTTPJsonClient
from .logging_config import configure_logging
from .models import DateSelection, JsonData, Warnings
from .storage import bolivia_now_iso, prepare_output_dirs, write_csv, write_json, write_text
from .validators import build_validation_summary


class JsonClient(Protocol):
    def get_json(self, url: str) -> JsonData:
        """Fetch JSON data from a URL-like key."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cndc_extractor",
        description="Extractor fase 1 de graficas publicas de operacion en tiempo real del CNDC.",
    )
    parser.add_argument("--fecha", help="Fecha manual para pruebas en formato YYYY-MM-DD.")
    parser.add_argument("--har", type=Path, help="Archivo HAR para leer respuestas guardadas.")
    parser.add_argument("--registros-frecuencia", type=int, help="Cantidad de registros de frecuencia.")
    parser.add_argument("--sin-raw", action="store_true", help="No guardar JSON crudo.")
    parser.add_argument("--salida", type=Path, default=Path("."), help="Directorio base de salida.")
    parser.add_argument("--verbose", action="store_true", help="Mostrar mas detalle en consola y log.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = Settings.load(output_base=args.salida)
        logger = configure_logging(settings.logs_directory, args.verbose)
        logger.info("Inicio de ejecucion CNDC extractor")
        result = run_extraction(args, settings, logger)
        print(_friendly_summary(result))
        logger.info("Fin de ejecucion CNDC extractor")
        return 0
    except CNDCExtractorError as exc:
        logging.getLogger("cndc_extractor").exception("Error controlado")
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        logging.getLogger("cndc_extractor").exception("Error inesperado")
        print(f"ERROR inesperado: {exc}")
        return 1


def run_extraction(args: argparse.Namespace, settings: Settings, logger: logging.Logger) -> dict[str, Any]:
    client: JsonClient
    read_mode = "HAR" if args.har else "API"
    if args.har:
        client = HARJsonClient(args.har)
    else:
        client = HTTPJsonClient(settings.http_timeout_seconds, settings.http_retries, logger)

    fechas_url = f"{settings.base_url}/fechas"
    fechas_raw = client.get_json(fechas_url)
    fechas_records = _as_list_of_dicts(fechas_raw, "fechas")
    if args.fecha:
        parsed = parse_operation_date(args.fecha)
        if parsed is None or args.fecha != parsed.isoformat():
            raise CNDCExtractorError("--fecha debe usar formato YYYY-MM-DD")
        selection = DateSelection(parsed, "MANUAL")
    else:
        selection = select_latest_realtime_date(fechas_records)
    operation_date = selection.operation_date
    logger.info("Fecha seleccionada: %s (%s)", operation_date.isoformat(), selection.mode)

    previous_date = operation_date - timedelta(days=1)
    seven_days_date = operation_date - timedelta(days=7)
    frequency_records = args.registros_frecuencia or settings.frequency_records
    urls = {
        "generacion_actual": f"{settings.base_url}/generacion?fecha={operation_date.isoformat()}",
        "generacion_ayer": f"{settings.base_url}/generacion?fecha={previous_date.isoformat()}",
        "generacion_7dias": f"{settings.base_url}/generacion?fecha={seven_days_date.isoformat()}",
        "demanda": f"{settings.base_url}/demanda?fecha={operation_date.isoformat()}",
        "frecuencia": f"{settings.base_url}/frecuencia/historial?registros={frequency_records}",
    }
    raw = {name: client.get_json(url) for name, url in urls.items()}

    gen_current = _as_list_of_dicts(raw["generacion_actual"], "generacion actual")
    gen_previous = _as_list_of_dicts(raw["generacion_ayer"], "generacion ayer")
    gen_seven = _as_list_of_dicts(raw["generacion_7dias"], "generacion hace siete dias")
    demand_records = _as_list_of_dicts(raw["demanda"], "demanda")
    frequency_raw = _as_list_of_dicts(raw["frecuencia"], "frecuencia")
    logger.info("Registros frecuencia recibidos: %s", len(frequency_raw))

    warnings = Warnings()
    generation_rows = normalize_generation(
        operation_date, gen_current, gen_previous, gen_seven, warnings, logger
    )
    demand_rows = normalize_demand(operation_date, demand_records, warnings, logger)
    frequency_rows = normalize_frequency(frequency_raw, settings.timezone, warnings, logger)

    output_paths = prepare_output_dirs(
        args.salida, settings.raw_data_directory, settings.normalized_data_directory, operation_date.isoformat()
    )
    if not args.sin_raw:
        write_json(output_paths.raw_dir / "fechas.json", fechas_raw)
        write_json(output_paths.raw_dir / f"generacion_{operation_date.isoformat()}.json", raw["generacion_actual"])
        write_json(output_paths.raw_dir / f"generacion_{previous_date.isoformat()}.json", raw["generacion_ayer"])
        write_json(output_paths.raw_dir / f"generacion_{seven_days_date.isoformat()}.json", raw["generacion_7dias"])
        write_json(output_paths.raw_dir / f"demanda_{operation_date.isoformat()}.json", raw["demanda"])
        write_json(output_paths.raw_dir / "frecuencia.json", raw["frecuencia"])

    write_csv(
        output_paths.normalized_dir / "generacion_normalizada.csv",
        generation_rows,
        ["fecha_operacion", "intervalo", "hora", "fecha_hora", "codigo", "serie", "comparacion", "mw"],
    )
    write_csv(
        output_paths.normalized_dir / "demanda_normalizada.csv",
        demand_rows,
        ["fecha_operacion", "intervalo", "hora", "fecha_hora", "codigo", "serie", "mw"],
    )
    write_csv(
        output_paths.normalized_dir / "frecuencia_normalizada.csv",
        frequency_rows,
        ["fecha_hora_original", "fecha_hora_bolivia", "fecha", "hora", "hz", "estado_rango"],
    )
    summary = build_validation_summary(
        operation_date,
        selection.mode,
        read_mode,
        generation_rows,
        demand_rows,
        frequency_rows,
        len(frequency_raw),
        warnings,
    )
    write_text(output_paths.normalized_dir / "resumen_validacion.txt", summary)

    metadata = {
        "fecha_operacion": operation_date.isoformat(),
        "modo_seleccion": selection.mode,
        "modo_lectura": read_mode,
        "fecha_ejecucion_bolivia": bolivia_now_iso(settings.timezone),
        "timezone": settings.timezone,
        "interpretacion_hora_frecuencia": "wall_clock_bolivia_with_misleading_z",
        "descripcion_hora_frecuencia": (
            "Los timestamps terminados en Z del endpoint CNDC se interpretan como "
            "hora local boliviana sin desplazamiento."
        ),
        "carpeta_raw": str(output_paths.raw_dir),
        "carpeta_normalized": str(output_paths.normalized_dir),
        "urls": urls,
    }
    write_json(output_paths.normalized_dir / "metadata.json", metadata)
    write_json(args.salida / "data" / "ultima_extraccion.json", metadata)
    logger.info("Archivos creados en %s y %s", output_paths.raw_dir, output_paths.normalized_dir)

    return {
        "metadata": metadata,
        "generation_rows": len(generation_rows),
        "demand_rows": len(demand_rows),
        "frequency_rows": len(frequency_rows),
        "warnings": warnings,
        "summary_path": output_paths.normalized_dir / "resumen_validacion.txt",
        "normalized_dir": output_paths.normalized_dir,
    }


def _as_list_of_dicts(data: JsonData, name: str) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise CNDCExtractorError(f"La respuesta de {name} no es una lista")
    result = [item for item in data if isinstance(item, dict)]
    if len(result) != len(data):
        raise CNDCExtractorError(f"La respuesta de {name} contiene elementos no validos")
    return cast(list[dict[str, Any]], result)


def _friendly_summary(result: dict[str, Any]) -> str:
    metadata = result["metadata"]
    warnings: Warnings = result["warnings"]
    return "\n".join(
        [
            "Extraccion CNDC completada.",
            f"Fecha de operacion: {metadata['fecha_operacion']} ({metadata['modo_seleccion']})",
            f"Modo de lectura: {metadata['modo_lectura']}",
            f"Carpeta normalizada: {result['normalized_dir']}",
            f"Filas generacion: {result['generation_rows']}",
            f"Filas demanda: {result['demand_rows']}",
            f"Filas frecuencia: {result['frequency_rows']}",
            "Advertencias: "
            + (
                "; ".join(
                    item
                    for item in [
                        f"generacion desconocida={','.join(sorted(warnings.unknown_generation_codes))}"
                        if warnings.unknown_generation_codes
                        else "",
                        f"demanda faltante={','.join(sorted(warnings.missing_demand_codes))}"
                        if warnings.missing_demand_codes
                        else "",
                        f"frecuencia invalida={warnings.frequency_invalid_records}"
                        if warnings.frequency_invalid_records
                        else "",
                    ]
                    if item
                )
                or "Ninguna"
            ),
        ]
    )
