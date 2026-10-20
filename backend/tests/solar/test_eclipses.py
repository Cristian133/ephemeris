"""Eclipses (Meeus cap. 54): ejemplos del libro, eclipses reales conocidos
(NASA/USNO) y propiedades de consistencia."""

from datetime import UTC, datetime, timedelta

import pytest

from app.solar.eclipses import (
    LunarKind,
    SolarKind,
    _elements,
    _geometry,
    eclipses_in_year,
    lunar_eclipse,
    solar_eclipse,
)
from app.solar.time import delta_t

# --- Ejemplos resueltos del libro ------------------------------------------


def test_example_54a_solar_eclipse_of_1993() -> None:
    el = _elements(-82)
    assert el.jde_mean == pytest.approx(2449128.5894, abs=1e-4)
    assert (el.m, el.mp, el.f, el.omega, el.f1) == pytest.approx(
        (135.9142, 244.5757, 165.7296, 253.0026, 165.7550), abs=1e-3
    )
    geometry = _geometry(el, solar=True)
    assert geometry.gamma == pytest.approx(1.1348, abs=1e-4)
    assert geometry.u == pytest.approx(0.0097, abs=1e-4)
    assert geometry.jde_max == pytest.approx(2449129.0979, abs=2e-4)  # 1993-05-21 14h21m TD

    eclipse = solar_eclipse(-82)
    assert eclipse is not None
    assert eclipse.kind is SolarKind.PARTIAL and not eclipse.central
    assert eclipse.magnitude == pytest.approx(0.740, abs=1e-3)


def test_example_54b_total_solar_eclipse_of_2009() -> None:
    el = _elements(118)
    assert el.jde_mean == pytest.approx(2455034.7071, abs=1e-4)
    assert (el.m, el.mp, el.f, el.f1) == pytest.approx(
        (196.9855, 7.9628, 179.8301, 179.8531), abs=1e-3
    )
    geometry = _geometry(el, solar=True)
    assert geometry.jde_max == pytest.approx(2455034.6088, abs=1e-4)
    assert geometry.gamma == pytest.approx(0.0695, abs=1e-4)
    assert geometry.u == pytest.approx(-0.0157, abs=1e-4)

    eclipse = solar_eclipse(118)
    assert eclipse is not None and eclipse.kind is SolarKind.TOTAL and eclipse.central
    assert eclipse.gamma > 0  # visible en el hemisferio norte


def test_example_54c_penumbral_lunar_eclipse_of_1973() -> None:
    el = _elements(-328.5)
    assert el.jde_mean == pytest.approx(2441849.2992, abs=1e-4)
    geometry = _geometry(el, solar=False)
    assert geometry.jde_max == pytest.approx(2441849.3687, abs=1e-4)
    assert geometry.gamma == pytest.approx(-1.3249, abs=1e-4)

    eclipse = lunar_eclipse(-328.5)
    assert eclipse is not None
    assert eclipse.kind is LunarKind.PENUMBRAL
    assert eclipse.umbral_magnitude == pytest.approx(-0.609, abs=1e-3)
    assert eclipse.penumbral_magnitude == pytest.approx(0.462, abs=1e-3)
    assert eclipse.total_start is None and eclipse.partial_start is None


def test_example_54d_total_lunar_eclipse_of_1997() -> None:
    eclipse = lunar_eclipse(-28.5)
    assert eclipse is not None and eclipse.kind is LunarKind.TOTAL
    assert eclipse.umbral_magnitude == pytest.approx(1.187, abs=2e-3)
    assert eclipse.gamma == pytest.approx(-0.3791, abs=1e-4)

    # Contactos del libro (UT, al minuto): 1997-09-16 16:14, 17:09, 18:17,
    # máximo 18:47, 19:17, 20:25, 21:20.
    expected = {
        "penumbra_start": (16, 14),
        "partial_start": (17, 9),
        "total_start": (18, 17),
        "time": (18, 47),
        "total_end": (19, 17),
        "partial_end": (20, 25),
        "penumbra_end": (21, 20),
    }
    for field, (hour, minute) in expected.items():
        moment = getattr(eclipse, field)
        assert moment is not None, field
        reference = datetime(1997, 9, 16, hour, minute, tzinfo=UTC)
        assert abs(moment - reference) < timedelta(minutes=2), field


def test_k_for_lunar_eclipse_must_be_a_full_moon() -> None:
    with pytest.raises(ValueError):
        lunar_eclipse(10)
    with pytest.raises(ValueError):
        lunar_eclipse(10.25)


def test_no_eclipse_when_the_moon_is_far_from_the_nodes() -> None:
    # Ejemplo 54.d: F = 125.26 para k = -30.5 (más de 21 grados de 180): sin eclipse.
    assert lunar_eclipse(-30.5) is None
    assert lunar_eclipse(-29.5) is None  # F = 155.93, tampoco
    assert solar_eclipse(-31) is None or solar_eclipse(-30) is None  # el mes sin nodo


# --- Eclipses reales (NASA) -------------------------------------------------
# (fecha y hora UT del máximo, tipo). El método da el máximo con un error
# medio de 0.4 min; se tolera 3 minutos.

_REAL_SOLAR = [
    (datetime(2023, 4, 20, 4, 16), SolarKind.HYBRID),
    (datetime(2023, 10, 14, 17, 59), SolarKind.ANNULAR),
    (datetime(2024, 4, 8, 18, 17), SolarKind.TOTAL),
    (datetime(2024, 10, 2, 18, 46), SolarKind.ANNULAR),
    (datetime(2025, 3, 29, 10, 48), SolarKind.PARTIAL),
    (datetime(2025, 9, 21, 19, 42), SolarKind.PARTIAL),
    (datetime(2026, 2, 17, 12, 12), SolarKind.ANNULAR),
    (datetime(2026, 8, 12, 17, 46), SolarKind.TOTAL),
]

_REAL_LUNAR = [
    (datetime(2023, 5, 5, 17, 23), LunarKind.PENUMBRAL),
    (datetime(2023, 10, 28, 20, 14), LunarKind.PARTIAL),
    (datetime(2024, 3, 25, 7, 13), LunarKind.PENUMBRAL),
    (datetime(2024, 9, 18, 2, 44), LunarKind.PARTIAL),
    (datetime(2025, 3, 14, 6, 59), LunarKind.TOTAL),
    (datetime(2025, 9, 7, 18, 12), LunarKind.TOTAL),
    (datetime(2026, 3, 3, 11, 34), LunarKind.TOTAL),
    (datetime(2026, 8, 28, 4, 13), LunarKind.PARTIAL),
]


@pytest.mark.parametrize("year", [2023, 2024, 2025, 2026])
def test_eclipses_of_2023_2026_match_the_real_ones(year: int) -> None:
    solar, lunar = eclipses_in_year(year)
    expected_solar = [e for e in _REAL_SOLAR if e[0].year == year]
    expected_lunar = [e for e in _REAL_LUNAR if e[0].year == year]
    assert [e.kind for e in solar] == [kind for _, kind in expected_solar]
    assert [e.kind for e in lunar] == [kind for _, kind in expected_lunar]
    for eclipse, (moment, _) in zip(solar + lunar, expected_solar + expected_lunar, strict=True):
        assert abs(eclipse.time - moment.replace(tzinfo=UTC)) < timedelta(minutes=3)


def test_book_exercises() -> None:
    # Ejercicios del cap. 54: cuatro eclipses solares parciales en el 2000;
    # tres eclipses lunares totales en 1982; el eclipse solar del 18 de abril
    # de 1977 fue anular; el primero de 1979 fue total y visible en el norte.
    solar_2000, _ = eclipses_in_year(2000)
    assert [e.kind for e in solar_2000] == [SolarKind.PARTIAL] * 4

    _, lunar_1982 = eclipses_in_year(1982)
    assert [e.kind for e in lunar_1982 if e.kind is LunarKind.TOTAL].__len__() == 3

    solar_1977, _ = eclipses_in_year(1977)
    april = next(e for e in solar_1977 if e.time.month == 4)
    assert april.kind is SolarKind.ANNULAR

    first_1979 = eclipses_in_year(1979)[0][0]
    assert first_1979.kind is SolarKind.TOTAL and first_1979.gamma > 0


def test_1991_had_four_lunar_eclipses_confirmed_by_independent_ephemeris() -> None:
    # Los cuatro (3 penumbrales y 1 parcial); gamma verificado con astropy
    # (1.076, 1.406, 1.437, 0.971 radios terrestres frente a 1.079, 1.410,
    # 1.441, 0.974 de este método).
    _, lunar = eclipses_in_year(1991)
    assert [e.kind for e in lunar] == [
        LunarKind.PENUMBRAL,
        LunarKind.PENUMBRAL,
        LunarKind.PENUMBRAL,
        LunarKind.PARTIAL,
    ]
    assert [abs(e.gamma) for e in lunar] == pytest.approx([1.076, 1.406, 1.437, 0.971], abs=0.01)


def test_every_year_has_between_four_and_seven_eclipses() -> None:
    for year in range(1990, 2060):
        solar, lunar = eclipses_in_year(year)
        assert 2 <= len(solar) <= 5, year
        assert 0 <= len(lunar) <= 4, year  # con los penumbrales, 4 es posible (1991)
        assert 4 <= len(solar) + len(lunar) <= 7, year
        assert all(e.time.year == year for e in solar + lunar)


def test_eclipses_are_chronological_and_separated_by_half_lunations() -> None:
    solar, lunar = eclipses_in_year(2024)
    assert [e.time for e in solar] == sorted(e.time for e in solar)
    for sun in solar:
        # todo eclipse solar tiene una Luna llena cerca (~15 días) que puede o no eclipsarse
        assert sun.time.year == 2024
    for moon in lunar:
        assert abs(moon.gamma) < 1.6


def test_lunar_contacts_are_ordered_and_symmetric_around_the_maximum() -> None:
    eclipse = lunar_eclipse(-28.5)
    assert eclipse is not None
    order = [
        eclipse.penumbra_start,
        eclipse.partial_start,
        eclipse.total_start,
        eclipse.time,
        eclipse.total_end,
        eclipse.partial_end,
        eclipse.penumbra_end,
    ]
    assert all(
        a is not None and b is not None and a < b for a, b in zip(order, order[1:], strict=False)
    )
    assert eclipse.time - eclipse.penumbra_start == eclipse.penumbra_end - eclipse.time


def test_partial_lunar_eclipse_has_no_totality() -> None:
    _, lunar = eclipses_in_year(2024)
    partial = next(e for e in lunar if e.kind is LunarKind.PARTIAL)
    assert partial.partial_start is not None and partial.partial_end is not None
    assert partial.total_start is None and partial.total_end is None
    assert 0 < partial.umbral_magnitude < 1


def test_times_are_universal_time_not_dynamical_time() -> None:
    # Dato del libro 54.a: el máximo es JDE 2449129.0979 (TD); la salida es UT.
    eclipse = solar_eclipse(-82)
    assert eclipse is not None
    td = datetime(1993, 5, 21, 14, 21, tzinfo=UTC)
    shift = (td - eclipse.time).total_seconds()
    assert shift == pytest.approx(delta_t(2449129.0979), abs=40)
