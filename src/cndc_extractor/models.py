"""Shared dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

JsonData = list[Any] | dict[str, Any]


@dataclass(frozen=True)
class DateSelection:
    operation_date: date
    mode: str


@dataclass
class Warnings:
    unknown_generation_codes: set[str] = field(default_factory=set)
    missing_demand_codes: set[str] = field(default_factory=set)
    frequency_invalid_records: int = 0
    frequency_timestamp_notes: set[str] = field(default_factory=set)
    frequency_z_timestamps: int = 0
    frequency_naive_timestamps: int = 0
    frequency_offset_timestamps: int = 0


@dataclass(frozen=True)
class OutputPaths:
    base: Path
    raw_dir: Path
    normalized_dir: Path
