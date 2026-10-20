from datetime import UTC, date, datetime

import numpy as np
import pytest

from app.solar.tides import (
    EARTH_RADIUS_M,
    MOON_TO_EARTH_MASS,
    SUN_TO_EARTH_MASS,
    day_tide_series,
    equilibrium_height,
    spring_neap_ratio,
    tide_extremes,
    tide_series,
)
from app.solar.time import julian_day

_MEAN_MOON_DISTANCE_KM = 384_400.0
_SUN_DISTANCE_KM = 149_597_870.7


def test_equilibrium_height_at_zenith_matches_the_textbook_value() -> None:
    # En el cenit: (m/M)(R/d)^3 R. La marea lunar de equilibrio es de unos 0.36 m.
    expected = (
        MOON_TO_EARTH_MASS
        * (EARTH_RADIUS_M / (_MEAN_MOON_DISTANCE_KM * 1000)) ** 3
        * EARTH_RADIUS_M
    )
    height = equilibrium_height(MOON_TO_EARTH_MASS, _MEAN_MOON_DISTANCE_KM, 90.0)
    assert height == pytest.approx(expected)
    assert 0.34 < height < 0.37


def test_equilibrium_height_has_two_bulges_and_the_right_ratios() -> None:
    zenith = equilibrium_height(MOON_TO_EARTH_MASS, _MEAN_MOON_DISTANCE_KM, 90.0)
    nadir = equilibrium_height(MOON_TO_EARTH_MASS, _MEAN_MOON_DISTANCE_KM, -90.0)
    horizon = equilibrium_height(MOON_TO_EARTH_MASS, _MEAN_MOON_DISTANCE_KM, 0.0)
    assert nadir == pytest.approx(zenith)  # el abultamiento opuesto es igual
    assert horizon == pytest.approx(-zenith / 2)  # cos^2 - 1/3: -1/3 contra +2/3


def test_equilibrium_height_averages_to_zero_over_the_sphere() -> None:
    # El volumen del océano se conserva: el promedio sobre la esfera es 0.
    angles = np.linspace(-90, 90, 20001)
    heights = equilibrium_height(MOON_TO_EARTH_MASS, _MEAN_MOON_DISTANCE_KM, angles)
    weights = np.cos(np.radians(angles))
    assert np.average(heights, weights=weights) == pytest.approx(0.0, abs=1e-6)


def test_sun_tide_is_about_46_percent_of_the_moon_tide() -> None:
    moon = equilibrium_height(MOON_TO_EARTH_MASS, _MEAN_MOON_DISTANCE_KM, 90.0)
    sun = equilibrium_height(SUN_TO_EARTH_MASS, _SUN_DISTANCE_KM, 90.0)
    assert sun / moon == pytest.approx(0.46, abs=0.02)


def test_equilibrium_height_vectorizes_and_is_closer_when_nearer() -> None:
    heights = equilibrium_height(MOON_TO_EARTH_MASS, np.array([357_000.0, 406_000.0]), 90.0)
    assert heights[0] > heights[1]


def test_total_is_moon_plus_sun() -> None:
    series = day_tide_series(date(2024, 4, 10), 20.0, -30.0)
    for moon, sun, total in zip(series.moon_m, series.sun_m, series.total_m, strict=True):
        assert total == pytest.approx(moon + sun)


def test_series_has_two_high_tides_per_lunar_day_at_the_equator() -> None:
    jd = julian_day(datetime(2024, 4, 10, tzinfo=UTC))
    extremes = tide_extremes(jd, 1.0, 0.0, 0.0)
    assert 3 <= len(extremes) <= 5
    # alternan pleamar y bajamar
    assert all(a.high != b.high for a, b in zip(extremes, extremes[1:], strict=False))
    highs = [e for e in extremes if e.high]
    lows = [e for e in extremes if not e.high]
    assert min(e.height_m for e in highs) > max(e.height_m for e in lows)
    # separación entre pleamares consecutivas: ~12h25m
    if len(highs) >= 2:
        spacing = (highs[1].time - highs[0].time).total_seconds() / 3600
        assert 12.0 < spacing < 12.9


def test_extremes_are_within_the_requested_interval() -> None:
    jd = julian_day(datetime(2024, 4, 10, tzinfo=UTC))
    for extreme in tide_extremes(jd, 2.0, 40.0, -3.7):
        assert datetime(2024, 4, 10, tzinfo=UTC) <= extreme.time < datetime(2024, 4, 12, tzinfo=UTC)


def _range(series) -> float:
    return max(series.total_m) - min(series.total_m)


def test_spring_tides_have_a_larger_range_than_neap_tides() -> None:
    # Luna nueva el 8 de abril de 2024 (sicigia) vs cuarto creciente el 15 (cuadratura).
    # Promedio del rango en 3 días de cada fase para suavizar la dependencia
    # de la declinación de la Luna.
    def mean_range(start: date) -> float:
        ranges = []
        for offset in range(3):
            day = date(start.year, start.month, start.day + offset)
            ranges.append(_range(day_tide_series(day, 10.0, 0.0)))
        return float(np.mean(ranges))

    assert mean_range(date(2024, 4, 8)) > 1.2 * mean_range(date(2024, 4, 15))


def test_spring_neap_ratio_peaks_at_syzygy_and_dips_at_quadrature() -> None:
    new_moon, full_moon = 2460409.2644, 2460424.4924
    first_quarter, last_quarter = 2460416.30, 2460430.5
    assert spring_neap_ratio(new_moon) > 1.3
    assert spring_neap_ratio(full_moon) > 1.3
    assert spring_neap_ratio(first_quarter) < 0.7
    assert spring_neap_ratio(last_quarter) < 0.7


def test_tide_series_length_and_step() -> None:
    jd = julian_day(datetime(2024, 4, 10, tzinfo=UTC))
    series = tide_series(jd, 1.0, 0.0, 0.0, step_minutes=30.0)
    assert len(series.times) == 48
    assert (series.times[1] - series.times[0]).total_seconds() == 1800
