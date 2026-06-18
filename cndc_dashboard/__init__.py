"""Compatibility package for running ``python -m cndc_dashboard`` from the repo root."""

from __future__ import annotations

from pathlib import Path

_src_package = Path(__file__).resolve().parent.parent / "src" / "cndc_dashboard"
if _src_package.exists():
    __path__.append(str(_src_package))
