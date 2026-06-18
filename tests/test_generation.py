import logging
from datetime import date

from cndc_extractor.generation import normalize_generation
from cndc_extractor.models import Warnings


def test_generation_intervals_nulls_comparisons_unknown_and_reno() -> None:
    warnings = Warnings()
    current = [
        {"codigo": "TOT", "valores": [1, -1] + [2] * 94},
        {"codigo": "RENO", "valores": [9] * 96},
        {"codigo": "FUTURO", "valores": [3] * 96},
    ]
    previous = [{"codigo": "TOT", "valores": [4] * 96}]
    seven = [{"codigo": "TOT", "valores": [5] * 96}]

    rows = normalize_generation(date(2026, 6, 18), current, previous, seven, warnings, logging.getLogger())

    assert len([row for row in rows if row["serie"] == "Total"]) == 96
    assert next(row for row in rows if row["serie"] == "Total" and row["intervalo"] == 2)["mw"] is None
    assert next(row for row in rows if row["serie"] == "Total" and row["intervalo"] == 96)["hora"] == "24:00"
    assert len([row for row in rows if row["serie"] == "Total Ayer"]) == 96
    assert len([row for row in rows if row["serie"] == "Total Hace 7 días"]) == 96
    assert "FUTURO" in warnings.unknown_generation_codes
    assert not any(row["codigo"] == "RENO" for row in rows)
