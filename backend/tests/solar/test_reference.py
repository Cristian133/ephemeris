"""Verificación contra referencias independientes del motor.

- Ejemplos numéricos del libro de Meeus (cap. 7, 10, 12, 22, 25).
- Horarios de orto/ocaso del Sol calculados con astropy (efemérides ERFA,
  no el método de baja precisión de esta app): para cada ubicación, el
  instante en que la altitud geométrica del Sol cruza -0.8333°, hallado
  por bisección. La tolerancia (20 s) es holgada frente al error medido
  (< 4 s en una grilla de 10 ubicaciones x 7 fechas x 3 umbrales) para no
  fallar por diferencias de redondeo entre versiones de numpy.
"""

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from app.solar.coordinates import declination, right_ascension
from app.solar.events import sunrise_sunset
from app.solar.horizontal import altitude, hour_angle, local_sidereal_time
from app.solar.nutation import nutation_in_longitude, nutation_in_obliquity, true_obliquity
from app.solar.time import (
    apparent_sidereal_time,
    julian_century,
    julian_century_tt,
    julian_day,
    mean_sidereal_time,
)

# Meeus cap. 22, ejemplo 22.a: 1987-04-10 0h TD (JDE 2446895.5).
_EXAMPLE_22A_JD = 2446895.5


def test_nutation_matches_meeus_example_22a() -> None:
    t = julian_century(_EXAMPLE_22A_JD)
    # Libro: Δψ = -3.788", Δε = +9.443", ε = 23°26'36.850". La versión corta
    # de la serie da Δψ con ~0.5" y Δε con ~0.1" de error.
    assert nutation_in_longitude(t) * 3600 == pytest.approx(-3.788, abs=0.5)
    assert nutation_in_obliquity(t) * 3600 == pytest.approx(9.443, abs=0.15)
    assert true_obliquity(t) == pytest.approx(23 + 26 / 60 + 36.850 / 3600, abs=1e-4)


def test_apparent_sidereal_time_matches_meeus_example_12a() -> None:
    # 1987-04-10 0h UT: tiempo sidéreo aparente 13h10m46.1351s.
    expected = (13 + 10 / 60 + 46.1351 / 3600) * 15
    assert apparent_sidereal_time(_EXAMPLE_22A_JD) == pytest.approx(expected, abs=3e-4)
    # y el medio, 13h10m46.3668s: la diferencia es la ecuación de los equinoccios.
    assert mean_sidereal_time(_EXAMPLE_22A_JD) == pytest.approx(197.693195, abs=1e-6)


def test_sun_position_matches_meeus_example_25a() -> None:
    # 1992-10-13 0h TD. Libro: α = 198.38083°, δ = -7.78507° (aparentes).
    t = -0.072183436
    assert right_ascension(t) == pytest.approx(198.38083, abs=0.01)
    assert declination(t) == pytest.approx(-7.78507, abs=0.01)


# (lugar, latitud, longitud este, día solar local, orto UT, ocaso UT): altitud
# geométrica -0.8333°, referencia astropy. Incluye longitudes al este de
# +150° (el amanecer cae el día UT anterior) y latitudes altas.
_ASTROPY_HORIZON = [
    ("Buenos Aires", -34.6, -58.4, date(2024, 6, 21), "2024-06-21T11:00:31", "2024-06-21T20:50:36"),
    ("Madrid", 40.4, -3.7, date(2024, 12, 21), "2024-12-21T07:34:30", "2024-12-21T16:51:40"),
    ("Sydney", -33.9, 151.2, date(2024, 1, 15), "2024-01-14T18:58:59", "2024-01-15T09:09:13"),
    ("Ushuaia", -54.8, -68.3, date(2024, 12, 21), "2024-12-21T07:51:38", "2024-12-22T01:11:30"),
    ("Auckland", -36.85, 174.76, date(2024, 3, 20), "2024-03-19T18:23:54", "2024-03-20T06:32:19"),
    ("Oulu", 65.0, 25.5, date(2024, 3, 20), "2024-03-20T04:17:22", "2024-03-20T16:35:01"),
    ("Oulu", 65.0, 25.5, date(2024, 9, 30), "2024-09-30T04:25:37", "2024-09-30T15:48:27"),
]


@pytest.mark.parametrize(
    ("place", "latitude", "longitude", "day", "sunrise", "sunset"),
    _ASTROPY_HORIZON,
    ids=[f"{case[0]}-{case[3]}" for case in _ASTROPY_HORIZON],
)
def test_sunrise_sunset_match_astropy(
    place: str, latitude: float, longitude: float, day: date, sunrise: str, sunset: str
) -> None:
    result = sunrise_sunset(day, latitude, longitude, altitude_deg=-0.8333)
    assert result.sunrise is not None
    assert result.sunset is not None
    tolerance = timedelta(seconds=20)
    assert abs(result.sunrise - datetime.fromisoformat(sunrise).replace(tzinfo=UTC)) < tolerance
    assert abs(result.sunset - datetime.fromisoformat(sunset).replace(tzinfo=UTC)) < tolerance


@pytest.mark.parametrize("latitude", [60.0, 64.0, 66.0, 68.0, 70.0, -60.0, -66.0, -68.0])
def test_horizon_crossing_has_the_requested_altitude_near_polar_circles(latitude: float) -> None:
    """Propiedad: a latitudes altas (donde el Sol roza el horizonte y los
    métodos basados en la pendiente de la altitud se vuelven inestables), el
    instante devuelto es realmente uno en que el Sol está a la altitud
    pedida. Se verifica con las funciones de posición, sin pasar por la
    iteración de `events`."""
    longitude = 15.0
    for day in (date(2024, 3, 1), date(2024, 5, 1), date(2024, 8, 1), date(2024, 11, 15)):
        for target in (-0.8333, -6.0):
            result = sunrise_sunset(day, latitude, longitude, altitude_deg=target)
            for moment in (result.sunrise, result.sunset):
                if moment is None:
                    continue
                jd = julian_day(moment)
                t = julian_century_tt(jd)
                lst = local_sidereal_time(apparent_sidereal_time(jd), longitude)
                h = hour_angle(lst, right_ascension(t))
                assert altitude(latitude, declination(t), h) == pytest.approx(target, abs=0.01)


def test_events_vectorized_year_has_no_nan_near_polar_circle() -> None:
    from app.solar.events import sunrise_sunset_year

    year = sunrise_sunset_year(2024, 66.5, 0.0)
    assert np.all(np.isfinite([moment.timestamp() for moment in year.transit]))
    assert year.always_above.count(None) > 300  # la mayoría de los días son normales
