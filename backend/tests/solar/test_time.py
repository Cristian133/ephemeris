from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from app.solar.time import (
    J2000,
    calendar_from_julian_day,
    datetime_from_julian_day,
    delta_t,
    julian_century,
    julian_century_tt,
    julian_day,
    julian_day_from_calendar,
    mean_sidereal_time,
)

J2000_MOMENT = datetime(2000, 1, 1, 12, 0, 0)


def test_j2000_epoch() -> None:
    assert julian_day(J2000_MOMENT) == pytest.approx(2_451_545.0)


def test_unix_epoch() -> None:
    assert julian_day(datetime(1970, 1, 1, 0, 0, 0)) == pytest.approx(2_440_587.5)


def test_naive_datetime_assumed_utc() -> None:
    naive = datetime(2024, 6, 15, 18, 30)
    aware = naive.replace(tzinfo=UTC)
    assert julian_day(naive) == julian_day(aware)


def test_timezone_aware_input_converted_to_utc() -> None:
    # 09:00 en Buenos Aires (UTC-3) == 12:00 UT == J2000.0
    local = datetime(2000, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
    assert julian_day(local) == pytest.approx(2_451_545.0)


@pytest.mark.parametrize(
    "delta",
    [
        timedelta(seconds=1),
        timedelta(hours=6),
        timedelta(days=1),
        timedelta(days=-1),
        timedelta(days=90),  # cruza fin de mes/trimestre
        timedelta(days=-400),  # cruza fin de año hacia atrás
        timedelta(days=10_000),  # ~27 años, cruza varios bisiestos
    ],
)
def test_matches_calendar_arithmetic(delta: timedelta) -> None:
    """El JD debe avanzar exactamente lo mismo que el calendario gregoriano
    proléptico de `datetime`, sin importar que la ventana cruce meses, años
    o siglos bisiestos.

    Tolerancia absoluta (no la relativa por default de `approx`): un JD
    ronda 2.45 millones, así que restar dos JD casi iguales en float64
    cancela los dígitos altos y deja ~1e-8 días (~1 ms) de piso de
    precisión — muy por debajo de lo que necesita esta app (la precisión
    del método de Meeus usado en `coordinates.py` es del orden de minutos).
    """
    expected_diff = delta.total_seconds() / 86_400
    actual_diff = julian_day(J2000_MOMENT + delta) - julian_day(J2000_MOMENT)
    assert actual_diff == pytest.approx(expected_diff, abs=1e-8)


def test_julian_century_at_epoch() -> None:
    assert julian_century(J2000) == pytest.approx(0.0)


@pytest.mark.parametrize("centuries", [1, -1, 2.5])
def test_julian_century_scales_linearly(centuries: float) -> None:
    jd = J2000 + centuries * 36_525.0
    assert julian_century(jd) == pytest.approx(centuries)


def test_datetime_from_julian_day_at_j2000_epoch() -> None:
    assert datetime_from_julian_day(J2000) == J2000_MOMENT.replace(tzinfo=UTC)


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC),
        datetime(1992, 10, 13, 0, 0, 0, tzinfo=UTC),
        datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC),
        datetime(2024, 2, 29, 18, 30, 15, tzinfo=UTC),  # 29 de febrero bisiesto
        datetime(1, 3, 1, 0, 0, 0, tzinfo=UTC),  # año 1, cruza el ajuste gregoriano
        datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),  # extremo del rango de datetime
    ],
)
def test_datetime_from_julian_day_is_inverse_of_julian_day(moment: datetime) -> None:
    assert datetime_from_julian_day(julian_day(moment)) == moment


def test_mean_sidereal_time_matches_meeus_example_12a() -> None:
    # Meeus, Astronomical Algorithms cap. 12, ejemplo 12.a: 1987 abril 10.0 UT.
    jd = julian_day(datetime(1987, 4, 10, 0, 0, 0, tzinfo=UTC))
    assert mean_sidereal_time(jd) == pytest.approx(197.693195, abs=1e-6)


def test_mean_sidereal_time_advances_about_361_degrees_per_day() -> None:
    # ~360.98565°/día: un poco más que una vuelta completa por día solar,
    # por el movimiento orbital de la Tierra (Meeus cap. 12).
    jd = J2000
    delta = mean_sidereal_time(jd + 1) - mean_sidereal_time(jd)
    assert delta == pytest.approx(0.98564736629, abs=1e-9)


def test_mean_sidereal_time_normalized_to_0_360() -> None:
    for jd in [J2000, J2000 + 12_345.6, J2000 - 98_765.4]:
        assert 0 <= mean_sidereal_time(jd) < 360


# --- Calendario juliano/gregoriano (Meeus cap. 7) --------------------------


@pytest.mark.parametrize(
    ("year", "month", "day", "calendar", "expected_jd"),
    [
        (1957, 10, 4.81, "auto", 2436116.31),  # ejemplo 7.a (Sputnik)
        (333, 1, 27.5, "auto", 1842713.0),  # ejemplo 7.b: juliano
        (2000, 1, 1.5, "auto", 2451545.0),  # J2000.0
        (1987, 1, 27.0, "auto", 2446822.5),
        (1987, 6, 19.5, "auto", 2446966.0),
        (1900, 1, 1.0, "auto", 2415020.5),
        (1600, 1, 1.0, "auto", 2305447.5),
        (1600, 12, 31.0, "auto", 2305812.5),
        (837, 4, 10.3, "auto", 2026871.8),
        (-123, 12, 31.0, "auto", 1676496.5),
        (-1000, 7, 12.5, "auto", 1356001.0),
        (-4712, 1, 1.5, "auto", 0.0),  # origen del Día Juliano
        (1582, 10, 4.0, "auto", 2299159.5),  # último día juliano
        (1582, 10, 15.0, "auto", 2299160.5),  # primer día gregoriano: sin hueco
    ],
)
def test_julian_day_from_calendar_matches_meeus_table(
    year: int, month: int, day: float, calendar: str, expected_jd: float
) -> None:
    assert julian_day_from_calendar(year, month, day, calendar) == pytest.approx(
        expected_jd, abs=1e-6
    )


def test_julian_day_from_calendar_reform_gap_does_not_exist() -> None:
    with pytest.raises(ValueError):
        julian_day_from_calendar(1582, 10, 10.0)


def test_julian_day_from_calendar_explicit_calendar_overrides_auto() -> None:
    # La misma fecha nominal en uno y otro calendario difiere en días.
    gregorian = julian_day_from_calendar(1500, 3, 1.0, "gregorian")
    julian = julian_day_from_calendar(1500, 3, 1.0, "julian")
    assert gregorian - julian == pytest.approx(-10.0)


def test_julian_day_from_calendar_rejects_unknown_calendar() -> None:
    with pytest.raises(ValueError):
        julian_day_from_calendar(2000, 1, 1.0, "maya")


@pytest.mark.parametrize(
    ("jd", "expected"),
    [
        (2436116.31, (1957, 10, 4.81, "gregorian")),
        (1842713.0, (333, 1, 27.5, "julian")),  # ejemplo 7.c: juliano
        (1507900.13, (-584, 5, 28.63, "julian")),  # ejemplo 7.c
        (2299159.5, (1582, 10, 4.0, "julian")),
        (2299160.5, (1582, 10, 15.0, "gregorian")),
        (0.0, (-4712, 1, 1.5, "julian")),
    ],
)
def test_calendar_from_julian_day_matches_meeus_examples(
    jd: float, expected: tuple[int, int, float, str]
) -> None:
    year, month, day, calendar = calendar_from_julian_day(jd)
    assert (year, month, calendar) == (expected[0], expected[1], expected[3])
    assert day == pytest.approx(expected[2], abs=1e-6)


def test_calendar_roundtrip_over_many_dates() -> None:
    for jd in np.linspace(1_000_000, 2_800_000, 500):
        year, month, day, calendar = calendar_from_julian_day(float(jd))
        assert julian_day_from_calendar(year, month, day, calendar) == pytest.approx(jd, abs=1e-5)


def test_calendar_from_julian_day_rejects_negative_jd() -> None:
    with pytest.raises(ValueError):
        calendar_from_julian_day(-1.0)


def test_gregorian_julian_day_agrees_with_datetime_based_function() -> None:
    assert julian_day(datetime(2024, 3, 20, 12, tzinfo=UTC)) == pytest.approx(
        julian_day_from_calendar(2024, 3, 20.5, "gregorian")
    )


# --- ΔT y escalas de tiempo ------------------------------------------------


def _jd_of_year(year: float) -> float:
    return J2000 + (year - 2000.0) * 365.2425


@pytest.mark.parametrize(
    ("year", "expected_seconds", "tolerance"),
    [
        (2000.5, 64.0, 0.3),  # medido (IERS)
        (2024.5, 69.19, 0.1),
        (1977.0, 48.0, 1.0),  # Meeus cap. 10
        (1900.0, -2.8, 1.0),
        (1700.0, 8.8, 0.5),
        (1000.0, 1574.0, 5.0),
    ],
)
def test_delta_t_matches_known_values(
    year: float, expected_seconds: float, tolerance: float
) -> None:
    assert delta_t(_jd_of_year(year)) == pytest.approx(expected_seconds, abs=tolerance)


def test_delta_t_is_continuous_across_the_whole_supported_range() -> None:
    # Los tramos del polinomio de Espenak y Meeus y el empalme con la tabla
    # medida no deben dejar saltos mayores a ~1.5 s entre años consecutivos
    # (salvo en épocas antiguas, donde ΔT crece rápido por sí mismo).
    previous = delta_t(_jd_of_year(1600.0))
    for year in np.arange(1600.5, 2100.0, 0.5):
        current = delta_t(_jd_of_year(float(year)))
        assert abs(current - previous) < 1.5, year
        previous = current


def test_julian_century_tt_is_ahead_of_ut_by_delta_t() -> None:
    jd = _jd_of_year(2024.5)
    difference_days = (julian_century_tt(jd) - julian_century(jd)) * 36525
    assert difference_days * 86400 == pytest.approx(delta_t(jd), abs=1e-3)


def test_julian_century_tt_vectorizes_and_keeps_scalar_type() -> None:
    jd = _jd_of_year(2024.5)
    assert isinstance(julian_century_tt(jd), float)
    result = julian_century_tt(jd + np.arange(5.0))
    assert result.shape == (5,)
    assert result[0] == pytest.approx(julian_century_tt(jd))
