"""Persistence helpers."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import OutputPaths


def prepare_output_dirs(base: Path, raw_root: Path, normalized_root: Path, operation_date: str) -> OutputPaths:
    raw_dir = raw_root / operation_date
    normalized_dir = normalized_root / operation_date
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    return OutputPaths(base=base, raw_dir=raw_dir, normalized_dir=normalized_dir)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = {key: ("" if row.get(key) is None else row.get(key)) for key in fieldnames}
            writer.writerow(clean)


def bolivia_now_iso(timezone_name: str) -> str:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(timezone_name)).isoformat()
