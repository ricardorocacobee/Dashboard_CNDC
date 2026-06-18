"""Prepare local Plotly JavaScript asset."""

from __future__ import annotations

import logging
from pathlib import Path

from plotly.offline import get_plotlyjs


def ensure_plotly_vendor(static_dir: Path, logger: logging.Logger) -> Path:
    vendor_path = static_dir / "vendor" / "plotly.min.js"
    if vendor_path.exists():
        return vendor_path
    vendor_path.parent.mkdir(parents=True, exist_ok=True)
    vendor_path.write_text(get_plotlyjs(), encoding="utf-8")
    logger.info("Archivo local Plotly.js generado: %s", vendor_path)
    return vendor_path
