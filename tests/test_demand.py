import logging
from datetime import date

from cndc_extractor.demand import normalize_demand
from cndc_extractor.models import Warnings


def test_demand_excludes_prev_scz_and_calculates_total_sin() -> None:
    warnings = Warnings()
    records = [
        {"codigo": "SANTA CRUZ", "valores": [1, -1] + [0] * 94},
        {"codigo": "LA PAZ", "valores": [2, -1] + [0] * 94},
        {"codigo": "COCHABAMBA", "valores": [3, -1] + [0] * 94},
        {"codigo": "POTOSI", "valores": [4, -1] + [0] * 94},
        {"codigo": "ORURO", "valores": [5, -1] + [0] * 94},
        {"codigo": "TARIJA", "valores": [6, -1] + [0] * 94},
        {"codigo": "CHUQUISACA", "valores": [7, -1] + [0] * 94},
        {"codigo": "BENI", "valores": [8, -1] + [0] * 94},
        {"codigo": "Prev.SCZ", "valores": [100] * 96},
    ]
    rows = normalize_demand(date(2026, 6, 18), records, warnings, logging.getLogger())

    assert not any(row["codigo"] == "Prev.SCZ" for row in rows)
    assert next(row for row in rows if row["codigo"] == "TOTAL_SIN" and row["intervalo"] == 1)["mw"] == 36
    assert next(row for row in rows if row["codigo"] == "TOTAL_SIN" and row["intervalo"] == 2)["mw"] is None
    assert not warnings.missing_demand_codes


def test_demand_does_not_zero_missing_and_detects_missing() -> None:
    warnings = Warnings()
    rows = normalize_demand(
        date(2026, 6, 18),
        [{"codigo": "SANTA CRUZ", "valores": [10]}],
        warnings,
        logging.getLogger(),
    )
    assert next(row for row in rows if row["codigo"] == "TOTAL_SIN" and row["intervalo"] == 1)["mw"] == 10
    assert next(row for row in rows if row["codigo"] == "TOTAL_SIN" and row["intervalo"] == 2)["mw"] is None
    assert "LA PAZ" in warnings.missing_demand_codes
