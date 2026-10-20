"""Perigeo y apogeo (Meeus cap. 50): ejemplo del libro, extremos de
distancia calculados con astropy y propiedades de consistencia."""

from datetime import UTC, datetime, timedelta

import pytest

from app.solar.apsides import ApsisKind, apsides_between, apsides_in_year, apsis
from app.solar.apsides_terms import (
    APOGEO_PARALAJE,
    APOGEO_TIEMPO,
    PERIGEO_PARALAJE,
    PERIGEO_TIEMPO,
)
from app.solar.time import delta_t, julian_day


def test_term_tables_have_the_rows_of_the_book() -> None:
    assert len(PERIGEO_TIEMPO) == 60
    assert len(APOGEO_TIEMPO) == 32
    assert len(PERIGEO_PARALAJE) == 46
    assert len(APOGEO_PARALAJE) == 17


def test_example_50a_apogee_of_october_1988() -> None:
    # Libro: JDE 2447442.3537 (20h29m TD), valor exacto 20h30m TD; paralaje
    # 3240.679" (0 54' 00.679"). La suma impresa por el libro (-0.4654 d) difiere
    # 0.0006 d de la que dan sus propias tablas (-0.46483): se acepta 1e-3 d.
    event = apsis(-148.5)
    assert event.kind is ApsisKind.APOGEE
    assert event.parallax_arcsec == pytest.approx(3240.679, abs=2e-3)
    jde = julian_day(event.time) + delta_t(2447442.35) / 86400
    assert jde == pytest.approx(2447442.3537, abs=1e-3)
    assert event.distance_km == pytest.approx(405_976.7, abs=1.0)


def test_k_must_be_integer_or_half_integer() -> None:
    with pytest.raises(ValueError):
        apsis(10.3)
    assert apsis(10).kind is ApsisKind.PERIGEE
    assert apsis(10.5).kind is ApsisKind.APOGEE


def test_perigee_of_december_1999_is_k_zero() -> None:
    event = apsis(0)
    assert abs(event.time - datetime(1999, 12, 22, 11, 0, tzinfo=UTC)) < timedelta(hours=1)


# Extremos de distancia de astropy (ERFA): (tipo, instante UT, distancia km).
_ASTROPY = [
    (ApsisKind.APOGEE, datetime(2025, 3, 17, 16, 27), 405729),
    (ApsisKind.PERIGEE, datetime(2025, 3, 30, 5, 19), 358137),
    (ApsisKind.PERIGEE, datetime(2025, 11, 5, 22, 36), 356830),
    (ApsisKind.APOGEE, datetime(2025, 11, 20, 3, 5), 406689),
]


@pytest.mark.parametrize(("kind", "moment", "distance"), _ASTROPY)
def test_apsides_match_astropy(kind: ApsisKind, moment: datetime, distance: float) -> None:
    events = apsides_between(moment - timedelta(days=2), moment + timedelta(days=2))
    event = next(e for e in events if e.kind is kind)
    # El libro declara errores de hasta ~31 min (perigeo) y ~3 min (apogeo)
    # frente a su teoría; frente a astropy se miden hasta 28 min y 18 min.
    assert abs(event.time - moment.replace(tzinfo=UTC)) < timedelta(minutes=35)
    assert event.distance_km == pytest.approx(distance, abs=60)


def test_apsides_alternate_and_stay_in_physical_range() -> None:
    events = apsides_in_year(2024)
    assert 24 <= len(events) <= 28  # ~13.4 perigeos + ~13.4 apogeos al año
    assert all(a.kind is not b.kind for a, b in zip(events, events[1:], strict=False))
    for event in events:
        if event.kind is ApsisKind.PERIGEE:
            assert 356_300 < event.distance_km < 370_500
        else:
            assert 404_000 < event.distance_km < 406_800


def test_perigee_to_perigee_interval_is_within_the_books_range() -> None:
    perigees = [e for e in apsides_in_year(2024) if e.kind is ApsisKind.PERIGEE]
    for a, b in zip(perigees, perigees[1:], strict=False):
        days = (b.time - a.time).total_seconds() / 86400
        assert 24.6 < days < 28.6  # el libro: de 24d16h a 28d13h


def test_apsides_are_chronological_and_within_the_requested_range() -> None:
    start, end = datetime(2024, 1, 1), datetime(2024, 7, 1)
    events = apsides_between(start, end)
    assert [e.time for e in events] == sorted(e.time for e in events)
    assert all(start.replace(tzinfo=UTC) <= e.time < end.replace(tzinfo=UTC) for e in events)


def test_closest_perigees_of_recent_years_match_known_supermoons() -> None:
    # Perigeos más cercanos: 2023-01-21 (356 568 km, el más cercano de la
    # década) y 2025-11-05 (356 834 km, el supermoon de noviembre).
    perigees = [
        e
        for year in range(2020, 2030)
        for e in apsides_in_year(year)
        if e.kind is ApsisKind.PERIGEE
    ]
    closest = min(perigees, key=lambda e: e.distance_km)
    assert closest.time.date().isoformat() == "2023-01-21"
    assert closest.distance_km == pytest.approx(356_568, abs=40)
    in_2025 = min((e for e in perigees if e.time.year == 2025), key=lambda e: e.distance_km)
    assert in_2025.time.date().isoformat() == "2025-11-05"
    assert in_2025.distance_km == pytest.approx(356_834, abs=40)
