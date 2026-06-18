from datetime import date

import pytest

from cndc_extractor.date_selector import select_latest_realtime_date
from cndc_extractor.exceptions import DateSelectionError


def test_selects_latest_tiempo_real() -> None:
    result = select_latest_realtime_date(
        [
            {"tipo": "TIEMPO_REAL", "fecha": "17.06.2026"},
            {"tipo": " tiempo_real ", "fecha": "2026-06-18"},
            {"tipo": "PREDESPACHO", "fecha": "2026-06-20"},
        ]
    )
    assert result.operation_date == date(2026, 6, 18)
    assert result.mode == "TIEMPO_REAL"


def test_ignores_invalid_dates_and_accepts_formats() -> None:
    result = select_latest_realtime_date(
        [
            {"tipo": "TIEMPO_REAL", "fecha": "nope"},
            {"tipo": "TIEMPO_REAL", "fecha": "18.06.2026"},
            {"tipo": "TIEMPO_REAL", "fecha": "2026-06-17"},
        ]
    )
    assert result.operation_date == date(2026, 6, 18)


def test_fallback_to_latest_general_without_tiempo_real() -> None:
    result = select_latest_realtime_date(
        [
            {"tipo": "POSTDESPACHO", "fecha": "2026-06-16"},
            {"tipo": "PREDESPACHO", "fecha": "18.06.2026"},
        ]
    )
    assert result.operation_date == date(2026, 6, 18)
    assert result.mode == "RESPALDO"


def test_fails_without_valid_dates() -> None:
    with pytest.raises(DateSelectionError):
        select_latest_realtime_date([{"tipo": "TIEMPO_REAL", "fecha": "x"}])
