"""Fases de la Luna: ejemplos de Meeus (cap. 49), horarios de astropy y
propiedades de consistencia con la posición de la Luna."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from app.solar.coordinates import apparent_longitude
from app.solar.moon import apparent_position
from app.solar.phase_terms import ADDITIONAL_CORRECTIONS, NEW_FULL_MOON_TERMS, QUARTER_TERMS
from app.solar.phases import (
    MEAN_SYNODIC_MONTH_DAYS,
    PhaseKind,
    moon_age_days,
    phase_jde,
    phase_time,
    phases_between,
    phases_in_year,
    previous_new_moon,
)
from app.solar.time import julian_century_tt, julian_day


def test_tables_have_the_rows_of_the_book() -> None:
    assert len(NEW_FULL_MOON_TERMS) == 25
    assert len(QUARTER_TERMS) == 25
    assert len(ADDITIONAL_CORRECTIONS) == 14


def test_new_moon_matches_meeus_example_49a() -> None:
    # Luna nueva de febrero de 1977 (k = -283): JDE 2443192.65118, es decir
    # 1977-02-18 3h37m42s TD.
    assert phase_jde(-283) == pytest.approx(2443192.65118, abs=1e-5)


def test_last_quarter_matches_meeus_example_49b() -> None:
    # Cuarto menguante de enero de 2044 (k = 544.75): JDE 2467636.49186.
    assert phase_jde(544.75) == pytest.approx(2467636.49186, abs=1e-5)


def test_phase_time_converts_dynamical_time_to_universal_time() -> None:
    # 3h37m42s TD con ΔT = 48 s en 1977: 3h36m54s UT.
    moment = phase_time(-283)
    assert abs(moment - datetime(1977, 2, 18, 3, 36, 54, tzinfo=UTC)) < timedelta(seconds=3)


def test_phase_jde_rejects_k_that_is_not_a_phase() -> None:
    with pytest.raises(ValueError):
        phase_jde(0.1)
    with pytest.raises(ValueError):
        phase_jde(12.3)


# Fases de abril de 2024 según astropy (elongación eclíptica aparente 0, 90,
# 180 y 270 grados); coinciden con el USNO al minuto.
_ASTROPY_APRIL_2024 = [
    (PhaseKind.LAST_QUARTER, "2024-04-02T03:14:45"),
    (PhaseKind.NEW, "2024-04-08T18:20:55"),
    (PhaseKind.FIRST_QUARTER, "2024-04-15T19:13:02"),
    (PhaseKind.FULL, "2024-04-23T23:49:02"),
]


def test_phases_of_april_2024_match_astropy() -> None:
    phases = phases_between(datetime(2024, 4, 1), datetime(2024, 4, 25))
    assert [p.kind for p in phases] == [kind for kind, _ in _ASTROPY_APRIL_2024]
    for phase, (_, moment) in zip(phases, _ASTROPY_APRIL_2024, strict=True):
        expected = datetime.fromisoformat(moment).replace(tzinfo=UTC)
        assert abs(phase.time - expected) < timedelta(seconds=40)


def test_phases_in_a_year_follow_the_cycle_and_the_synodic_month() -> None:
    phases = phases_in_year(2025)
    assert 48 <= len(phases) <= 50  # 12.37 lunaciones x 4
    kinds = [int(p.kind) for p in phases]
    assert all((b - a) % 4 == 1 for a, b in zip(kinds, kinds[1:], strict=False))
    assert all(p.time.year == 2025 for p in phases)
    new_moons = [p for p in phases if p.kind is PhaseKind.NEW]
    for a, b in zip(new_moons, new_moons[1:], strict=False):
        days = (b.time - a.time).total_seconds() / 86400
        assert 29.2 < days < 29.9  # lunaciones extremas del siglo: 29.27 a 29.83 días


def test_phases_between_is_chronological_and_respects_the_range() -> None:
    start, end = datetime(2024, 1, 1), datetime(2024, 4, 1)
    phases = phases_between(start, end)
    times = [p.time for p in phases]
    assert times == sorted(times)
    assert all(start.replace(tzinfo=UTC) <= t < end.replace(tzinfo=UTC) for t in times)


def test_phase_instants_have_the_right_elongation_from_the_moon_position() -> None:
    """Consistencia interna entre dos módulos independientes (las series de
    posición del cap. 47 y las fases del cap. 49): en el instante de cada
    fase, la longitud de la Luna menos la del Sol es 0, 90, 180 o 270."""
    for phase in phases_in_year(2024):
        jd = julian_day(phase.time)
        t = julian_century_tt(jd)
        elongation = (float(apparent_position(t).longitude) - float(apparent_longitude(t))) % 360
        expected = int(phase.kind) * 90
        error = (elongation - expected + 180) % 360 - 180
        assert abs(error) < 0.12, (phase, error)  # 0.12 grados = ~10 minutos de tiempo


def test_brown_lunation_numbering() -> None:
    # Luna nueva del 6 de enero de 2000 = lunación 953; k = 0.
    first = phases_between(datetime(2000, 1, 5), datetime(2000, 1, 8))
    assert len(first) == 1 and first[0].kind is PhaseKind.NEW
    assert first[0].brown_lunation == 953


def test_moon_age() -> None:
    new_moon = phase_time(0)
    jd = julian_day(new_moon)
    assert moon_age_days(jd + 0.0001) == pytest.approx(0.0001, abs=1e-6)
    assert moon_age_days(jd + 10.0) == pytest.approx(10.0, abs=1e-6)
    assert moon_age_days(jd + 29.0) == pytest.approx(29.0, abs=1e-6)
    assert 0 <= moon_age_days(jd + 59.0) < MEAN_SYNODIC_MONTH_DAYS + 1


def test_previous_new_moon_is_before_the_instant() -> None:
    for offset in np.linspace(0, 60, 25):
        jd = julian_day(datetime(2024, 4, 1, tzinfo=UTC)) + float(offset)
        previous = previous_new_moon(jd)
        assert julian_day(previous.time) <= jd
        assert jd - julian_day(previous.time) < 29.9
