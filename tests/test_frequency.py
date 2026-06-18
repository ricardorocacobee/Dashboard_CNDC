import logging

from cndc_extractor.frequency import normalize_frequency, parse_cndc_frequency_timestamp
from cndc_extractor.models import Warnings


def test_parse_cndc_frequency_timestamp_misleading_z_without_shift() -> None:
    result = parse_cndc_frequency_timestamp("2026-06-18T10:08:55Z")
    assert result.isoformat() == "2026-06-18T10:08:55-04:00"


def test_parse_cndc_frequency_timestamp_naive_without_shift() -> None:
    result = parse_cndc_frequency_timestamp("2026-06-18T10:08:55")
    assert result.isoformat() == "2026-06-18T10:08:55-04:00"


def test_parse_cndc_frequency_timestamp_explicit_offset_converts() -> None:
    result = parse_cndc_frequency_timestamp("2026-06-18T14:08:55+00:00")
    assert result.isoformat() == "2026-06-18T10:08:55-04:00"


def test_parse_cndc_frequency_timestamp_bolivia_offset_is_stable() -> None:
    result = parse_cndc_frequency_timestamp("2026-06-18T10:08:55-04:00")
    assert result.isoformat() == "2026-06-18T10:08:55-04:00"


def test_frequency_orders_dedupes_converts_and_classifies() -> None:
    warnings = Warnings()
    rows = normalize_frequency(
        [
            {"valor": 50.5, "hora": "2026-06-18T10:00:00Z"},
            {"valor": 49.952, "hora": "2026-06-18T09:00:00Z"},
            {"valor": 49.9, "hora": "2026-06-18T09:00:00Z"},
            {"valor": "bad", "hora": "x"},
        ],
        "America/La_Paz",
        warnings,
        logging.getLogger(),
    )
    assert len(rows) == 2
    assert rows[0]["fecha_hora_original"] == "2026-06-18T09:00:00Z"
    assert rows[0]["fecha_hora_bolivia"] == "2026-06-18T09:00:00-04:00"
    assert rows[0]["hora"] == "09:00:00"
    assert rows[0]["hz"] == 49.9
    assert rows[0]["estado_rango"] == "Normal"
    assert rows[1]["estado_rango"] == "Fuera de rango"
    assert warnings.frequency_invalid_records == 1
    assert warnings.frequency_z_timestamps == 3


def test_frequency_does_not_shift_1008_to_0608() -> None:
    warnings = Warnings()
    rows = normalize_frequency(
        [
            {"valor": 50.058, "hora": "2026-06-18T10:08:55Z"},
            {"valor": 50.4, "hora": "2026-06-18T10:08:56Z"},
        ],
        "America/La_Paz",
        warnings,
        logging.getLogger(),
    )
    assert rows[0]["fecha_hora_original"] == "2026-06-18T10:08:55Z"
    assert rows[0]["fecha_hora_bolivia"] == "2026-06-18T10:08:55-04:00"
    assert rows[0]["hora"] == "10:08:55"
    assert rows[0]["estado_rango"] == "Normal"
    assert rows[1]["estado_rango"] == "Fuera de rango"


def test_frequency_naive_timestamp_is_assigned_bolivia() -> None:
    warnings = Warnings()
    rows = normalize_frequency(
        [{"valor": 50.01, "hora": "2026-06-18T09:00:00"}],
        "America/La_Paz",
        warnings,
        logging.getLogger(),
    )
    assert rows[0]["fecha_hora_bolivia"].endswith("-04:00")
    assert "ingenuos" in next(iter(warnings.frequency_timestamp_notes))
