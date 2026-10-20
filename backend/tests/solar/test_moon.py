"""Posición, iluminación y eventos de la Luna.

Referencias: ejemplos numéricos de Meeus (caps. 40, 47 y 48) y posiciones y
horarios calculados con astropy (efemérides ERFA independientes). Las
tolerancias son holgadas frente al error medido para no fallar por
diferencias de versión.
"""

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from app.solar.moon import (
    apparent_position,
    ecliptic_to_equatorial,
    geocentric_ecliptic,
    horizontal_parallax,
    illumination,
    mean_elements,
    moon_day,
    moon_trajectory,
    topocentric_equatorial,
)
from app.solar.moon_terms import LATITUDE_TERMS, LONGITUDE_DISTANCE_TERMS
from app.solar.time import julian_century, julian_century_tt

# Meeus cap. 47, ejemplo 47.a: 1992-04-12 0h TD (JDE 2448724.5).
_EXAMPLE_47A_T = julian_century(2448724.5)


def test_term_tables_have_the_sixty_rows_of_the_book() -> None:
    assert len(LONGITUDE_DISTANCE_TERMS) == 60
    assert len(LATITUDE_TERMS) == 60
    assert len({row[:4] for row in LONGITUDE_DISTANCE_TERMS}) == 60  # sin filas repetidas
    assert len({row[:4] for row in LATITUDE_TERMS}) == 60


def test_mean_elements_match_meeus_example_47a() -> None:
    lp, d, m, mp, f = mean_elements(_EXAMPLE_47A_T)
    assert lp == pytest.approx(134.290182, abs=1e-5)
    assert d == pytest.approx(113.842304, abs=1e-5)
    assert m == pytest.approx(97.643514, abs=1e-5)
    assert mp == pytest.approx(5.150833, abs=1e-5)
    assert f == pytest.approx(219.889721, abs=1e-5)


def test_geocentric_position_matches_meeus_example_47a() -> None:
    longitude, latitude, distance = geocentric_ecliptic(_EXAMPLE_47A_T)
    assert longitude == pytest.approx(133.162655, abs=2e-6)
    assert latitude == pytest.approx(-3.229126, abs=2e-6)
    assert distance == pytest.approx(368409.7, abs=0.1)
    assert horizontal_parallax(distance) == pytest.approx(0.991990, abs=1e-6)


def test_apparent_position_matches_meeus_example_47a() -> None:
    # Libro: λ aparente 133.167265 (con Δψ = +0.004610), α = 134.688470, δ = 13.768368.
    position = apparent_position(_EXAMPLE_47A_T)
    assert position.longitude == pytest.approx(133.167265, abs=2e-4)
    assert position.right_ascension == pytest.approx(134.688470, abs=2e-4)
    assert position.declination == pytest.approx(13.768368, abs=2e-4)


def test_position_vectorizes_and_matches_scalar_calls() -> None:
    t = _EXAMPLE_47A_T + np.linspace(0, 0.001, 7)
    longitude, latitude, distance = geocentric_ecliptic(t)
    assert longitude.shape == latitude.shape == distance.shape == (7,)
    for i in (0, 3, 6):
        scalar = geocentric_ecliptic(float(t[i]))
        assert (longitude[i], latitude[i], distance[i]) == pytest.approx(scalar)


def test_moon_stays_within_physical_bounds() -> None:
    t = np.linspace(-0.5, 0.5, 4000)
    longitude, latitude, distance = geocentric_ecliptic(t)
    assert np.all(np.abs(latitude) < 5.4)  # inclinación orbital ~5.15° más perturbaciones
    assert np.all((distance > 350_000) & (distance < 410_000))
    assert np.all((longitude >= 0) & (longitude < 360))


# ecuatoriales aparentes (TETE) geocéntricas de astropy: JD en UT -> (α, δ, Δ)
_ASTROPY_POSITIONS = [
    (2451545.0, 222.45233, -10.90026, 402412.8),
    (2455197.5, 104.46491, 23.49987, 359364.4),
    (2460400.25, 249.43168, -26.52919, 390709.8),
]


@pytest.mark.parametrize(("jd", "ra", "dec", "distance"), _ASTROPY_POSITIONS)
def test_apparent_position_matches_astropy(
    jd: float, ra: float, dec: float, distance: float
) -> None:
    position = apparent_position(julian_century_tt(jd))
    assert position.right_ascension == pytest.approx(ra, abs=0.002)  # ~7"
    assert position.declination == pytest.approx(dec, abs=0.002)
    assert position.distance_km == pytest.approx(distance, abs=100)


def test_ecliptic_to_equatorial_identities() -> None:
    eps = 23.4393
    alpha, delta = ecliptic_to_equatorial(0.0, 0.0, eps)
    assert (alpha, delta) == pytest.approx((0.0, 0.0), abs=1e-9)
    alpha, delta = ecliptic_to_equatorial(90.0, 0.0, eps)
    assert (alpha, delta) == pytest.approx((90.0, eps))
    # Un punto en el polo norte de la eclíptica está a 90 - ε de declinación.
    _, delta = ecliptic_to_equatorial(0.0, 90.0, eps)
    assert delta == pytest.approx(90 - eps)


@pytest.mark.parametrize(
    ("alpha", "delta", "distance_km", "h", "latitude", "elevation"),
    [
        (134.69, 13.77, 368_409.7, 40.0, 40.4, 0.0),
        (10.0, -25.0, 400_000.0, -75.0, -34.6, 600.0),
        (200.0, 5.0, 357_000.0, 100.0, 0.0, 0.0),
        (300.0, 60.0, 385_000.0, -10.0, 65.0, 2000.0),
    ],
)
def test_topocentric_correction_matches_the_rigorous_vector_method(
    alpha: float, delta: float, distance_km: float, h: float, latitude: float, elevation: float
) -> None:
    """Verificación independiente de la fórmula de Meeus (cap. 40): restar al
    vector geocéntrico de la Luna el vector del observador (elipsoide
    terrestre) y reconvertir a α, δ y H."""
    alpha_topo, delta_topo, h_topo = topocentric_equatorial(
        alpha, delta, distance_km, h, latitude, elevation
    )

    a_e = 6378.14
    phi = np.radians(latitude)
    u = np.arctan(0.99664719 * np.tan(phi))
    rho_sin = 0.99664719 * np.sin(u) + elevation / 6378140 * np.sin(phi)
    rho_cos = np.cos(u) + elevation / 6378140 * np.cos(phi)
    sidereal = np.radians(alpha + h)  # tiempo sidéreo local = α + H
    observer = a_e * np.array([rho_cos * np.cos(sidereal), rho_cos * np.sin(sidereal), rho_sin])
    a, d = np.radians(alpha), np.radians(delta)
    moon = distance_km * np.array([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)])
    x, y, z = moon - observer
    expected_alpha = np.degrees(np.arctan2(y, x)) % 360
    expected_delta = np.degrees(np.arctan2(z, np.hypot(x, y)))

    assert alpha_topo == pytest.approx(expected_alpha, abs=1e-5)
    assert delta_topo == pytest.approx(expected_delta, abs=1e-5)
    assert h_topo == pytest.approx(alpha + h - expected_alpha, abs=1e-5)


def test_topocentric_correction_vanishes_at_zenith_of_a_distant_object() -> None:
    alpha, delta, h = topocentric_equatorial(100.0, 40.0, 1e9, 0.0, 40.0)
    assert (alpha, delta, h) == pytest.approx((100.0, 40.0, 0.0), abs=1e-4)


def test_horizontal_parallax_of_the_mean_lunar_distance() -> None:
    assert horizontal_parallax(384_400.0) == pytest.approx(0.9507, abs=1e-3)


# --- Iluminación (Meeus cap. 48) -------------------------------------------


def test_illumination_matches_meeus_example_48a() -> None:
    # 1992-04-12 0h TD: k = 0.6786, i = 69.0756° (alta precisión), χ = 285.0°
    # (ángulo del limbo brillante), Luna creciente. El libro da ΔT = 59 s.
    jd_ut = 2448724.5 - 59 / 86400
    result = illumination(jd_ut)
    assert result.phase_angle_deg == pytest.approx(69.0756, abs=0.01)
    assert result.fraction == pytest.approx(0.6786, abs=1e-4)
    assert result.bright_limb_angle_deg == pytest.approx(285.0, abs=0.5)
    assert result.waxing


def test_illumination_at_new_and_full_moon() -> None:
    new = illumination(2460409.2644)  # luna nueva del 8 de abril de 2024, 18:21 UT
    full = illumination(2460424.4924)  # luna llena del 23 de abril de 2024, 23:49 UT
    assert new.fraction < 0.001
    assert new.phase_angle_deg > 179
    assert full.fraction > 0.99


def test_illumination_is_consistent_over_a_lunation() -> None:
    start = 2460408.0
    fractions = [illumination(start + d).fraction for d in np.arange(0, 29.5, 0.5)]
    assert min(fractions) < 0.01 and max(fractions) > 0.99
    waxing = [illumination(start + d).waxing for d in (3.0, 6.0, 20.0, 25.0)]
    assert waxing == [True, True, False, False]


# --- Salida, tránsito y puesta ----------------------------------------------

# (lugar, latitud, longitud este, día local, orto UT, ocaso UT): centro de la
# Luna a -0.8367° de altitud topocéntrica, referencia astropy.
_ASTROPY_MOONRISE = [
    ("Buenos Aires", -34.6, -58.4, date(2024, 4, 10), "2024-04-10T12:20:20", "2024-04-10T22:45:17"),
    ("Madrid", 40.4, -3.7, date(2024, 4, 10), "2024-04-10T06:31:28", "2024-04-10T21:20:53"),
    ("Sydney", -33.9, 151.2, date(2024, 4, 10), "2024-04-09T21:37:37", "2024-04-10T08:26:19"),
    ("Oulu", 65.0, 25.5, date(2024, 4, 10), "2024-04-10T02:50:16", "2024-04-10T21:48:33"),
]


@pytest.mark.parametrize(
    ("place", "latitude", "longitude", "day", "rise", "set_"),
    _ASTROPY_MOONRISE,
    ids=[case[0] for case in _ASTROPY_MOONRISE],
)
def test_moonrise_and_moonset_match_astropy(
    place: str, latitude: float, longitude: float, day: date, rise: str, set_: str
) -> None:
    result = moon_day(day, latitude, longitude)
    assert result.rise is not None and result.set is not None
    tolerance = timedelta(seconds=45)
    assert abs(result.rise - datetime.fromisoformat(rise).replace(tzinfo=UTC)) < tolerance
    assert abs(result.set - datetime.fromisoformat(set_).replace(tzinfo=UTC)) < tolerance


def test_moon_transit_is_between_rise_and_set_and_is_the_highest_point() -> None:
    day, lat, lon = date(2024, 4, 10), 40.4, -3.7
    result = moon_day(day, lat, lon)
    assert result.rise is not None and result.set is not None and result.transit is not None
    assert result.rise < result.transit < result.set
    trajectory = moon_trajectory(day, lat, lon, num_samples=288)
    peak = max(trajectory.altitude)
    assert result.transit_altitude_deg == pytest.approx(
        peak, abs=0.6
    )  # geocéntrica vs topocéntrica


def test_moon_misses_an_event_roughly_once_a_month() -> None:
    # La Luna sale ~50 min más tarde cada día: en algún día del mes no sale
    # dentro del día local (y en otro no se pone). En un mes debe pasar ambas cosas.
    days = [date(2024, 4, 1) + timedelta(days=i) for i in range(30)]
    results = [moon_day(d, 40.4, -3.7) for d in days]
    assert sum(r.rise is None for r in results) == 1
    assert sum(r.set is None for r in results) == 1


def test_moon_rises_about_50_minutes_later_each_day() -> None:
    first = moon_day(date(2024, 4, 10), 40.4, -3.7).rise
    second = moon_day(date(2024, 4, 11), 40.4, -3.7).rise
    assert first is not None and second is not None
    delay = (second - first - timedelta(days=1)).total_seconds() / 60
    assert 20 < delay < 90


def test_moon_never_sets_or_rises_at_high_latitudes_some_days() -> None:
    # Cerca del solsticio de invierno boreal, a 80° N la Luna puede quedar
    # circumpolar o siempre bajo el horizonte durante días.
    results = [moon_day(date(2024, 12, 15) + timedelta(days=i), 80.0, 0.0) for i in range(15)]
    flags = {r.always_above for r in results if r.rise is None and r.set is None}
    assert flags == {True, False}


# --- Trayectoria -------------------------------------------------------------


def test_trajectory_has_requested_samples_and_valid_angles() -> None:
    result = moon_trajectory(date(2024, 4, 10), -34.6, -58.4, num_samples=48)
    assert len(result.times) == len(result.altitude) == len(result.azimuth) == 48
    assert all(-90 <= a <= 90 for a in result.altitude)
    assert all(0 <= z < 360 for z in result.azimuth)
    assert 0 <= result.illuminated_fraction <= 1


def test_trajectory_parallax_lowers_the_moon_by_parallax_times_cosine_of_altitude() -> None:
    """La altitud topocéntrica es menor que la geocéntrica por ~π·cos(h)
    (π: paralaje horizontal, ~0.95-1.02° según la distancia)."""
    from app.solar.horizontal import altitude, hour_angle, local_sidereal_time
    from app.solar.time import apparent_sidereal_time, julian_day

    day, lat, lon = date(2024, 4, 10), 40.4, -3.7
    result = moon_trajectory(day, lat, lon, num_samples=96)
    for time, topo_alt in zip(result.times, result.altitude, strict=True):
        jd = julian_day(time)
        position = apparent_position(julian_century_tt(jd))
        h = hour_angle(
            local_sidereal_time(apparent_sidereal_time(jd), lon), position.right_ascension
        )
        geocentric_alt = altitude(lat, position.declination, h)
        parallax = horizontal_parallax(position.distance_km)
        expected = parallax * np.cos(np.radians(geocentric_alt))
        assert geocentric_alt - topo_alt == pytest.approx(expected, abs=0.02)
