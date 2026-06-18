"""CLI for the local dashboard."""

from __future__ import annotations

import argparse

import uvicorn

from .app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cndc_dashboard",
        description="Dashboard local de prueba para graficas CNDC.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host de escucha.")
    parser.add_argument("--port", type=int, default=8000, help="Puerto de escucha.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print("Dashboard CNDC disponible en:")
    print(f"http://{args.host}:{args.port}")
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")
    return 0
