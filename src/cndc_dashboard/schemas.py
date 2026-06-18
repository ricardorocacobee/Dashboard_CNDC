"""Shared response helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChartSeries:
    codigo: str
    nombre: str
    valores: list[float | None]

    def as_dict(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "nombre": self.nombre, "valores": self.valores}
