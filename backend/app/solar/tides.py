"""Mareas teóricas: la marea de equilibrio que producen la Luna y el Sol.

Es la deformación que adoptaría un océano que cubriera toda la Tierra y
respondiera al instante a la atracción diferencial (fuerza de marea) del
Sol y la Luna. Para un cuerpo de masa `m` a distancia `d`, la altura de
equilibrio sobre el nivel medio en un punto cuyo cenit forma el ángulo
ψ con la dirección al cuerpo es

    η = (3/2) · (m / M_tierra) · (R / d)^3 · R · (cos²ψ - 1/3)

(teoría de equilibrio de Newton; ver el *Explanatory Supplement* y
Vallado para la teoría de las mareas). Da una abultamiento hacia el cuerpo
y otro opuesto (dos pleamares por día lunar), y la suma de Luna y Sol
reproduce el ciclo de mareas vivas (sicigias: Luna nueva y llena, ambos
abultamientos alineados) y muertas (cuadraturas).

Alcance y límites: es una cantidad astronómica, no la altura de la marea
real de un puerto. La marea real depende de la forma de las cuencas
oceánicas, la profundidad, las costas y la resonancia, que pueden
multiplicar o desfasar el valor de equilibrio varias veces (en bahías
como Fundy llega a 15 m; en el Mediterráneo es de centímetros). Sirve
para saber *cuándo* y *cuánto* tira el Sol y la Luna, y para el ciclo
vivas/muertas, no para predecir la altura en una costa concreta. No incluye
la respuesta elástica de la Tierra sólida (números de Love) ni la
inercia del océano.
"""

from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
from numpy.typing import NDArray

from app.solar.coordinates import apparent_longitude, declination, radius_vector, right_ascension
from app.solar.events import local_day_start_jd
from app.solar.horizontal import altitude, hour_angle, local_sidereal_time
from app.solar.moon import ASTRONOMICAL_UNIT_KM, apparent_position
from app.solar.time import apparent_sidereal_time, datetime_from_julian_day, julian_century_tt

EARTH_RADIUS_M = 6_378_140.0
MOON_TO_EARTH_MASS = 0.0123000371
SUN_TO_EARTH_MASS = 332_946.05

Array = NDArray[np.floating]


def equilibrium_height(
    body_to_earth_mass: float, distance_km: Array | float, body_altitude_deg: Array | float
) -> Array | float:
    """Altura de equilibrio (m) por un cuerpo de masa relativa a la Tierra
    `body_to_earth_mass`, a `distance_km`, visto a `body_altitude_deg` de
    altitud geocéntrica (el ángulo cenital ψ es 90° menos eso)."""
    distance_m = np.asarray(distance_km) * 1000.0
    cos_psi = np.sin(np.radians(body_altitude_deg))
    return (
        1.5
        * body_to_earth_mass
        * (EARTH_RADIUS_M / distance_m) ** 3
        * EARTH_RADIUS_M
        * (cos_psi**2 - 1 / 3)
    )


@dataclass(frozen=True)
class TideSeries:
    """Marea de equilibrio a lo largo de un intervalo, en metros sobre el
    nivel medio: la de la Luna, la del Sol y su suma."""

    times: list[datetime]
    moon_m: list[float]
    sun_m: list[float]
    total_m: list[float]


@dataclass(frozen=True)
class TideExtreme:
    """Pleamar (`high`) o bajamar (`low`) de equilibrio."""

    time: datetime
    height_m: float
    high: bool


def _state(jd: Array, latitude_deg: float, longitude_deg: float) -> tuple[Array, Array, Array]:
    """Alturas de equilibrio (Luna, Sol, total) en los instantes `jd` (UT)."""
    t = julian_century_tt(jd)
    gst = apparent_sidereal_time(jd)
    lst = local_sidereal_time(gst, longitude_deg)

    moon = apparent_position(t)
    moon_alt = altitude(latitude_deg, moon.declination, hour_angle(lst, moon.right_ascension))
    sun_alt = altitude(latitude_deg, declination(t), hour_angle(lst, right_ascension(t)))
    moon_height = equilibrium_height(MOON_TO_EARTH_MASS, moon.distance_km, moon_alt)
    sun_height = equilibrium_height(
        SUN_TO_EARTH_MASS, radius_vector(t) * ASTRONOMICAL_UNIT_KM, sun_alt
    )
    return moon_height, sun_height, moon_height + sun_height


def tide_series(
    start_jd: float,
    duration_days: float,
    latitude_deg: float,
    longitude_deg: float,
    step_minutes: float = 10.0,
) -> TideSeries:
    """Marea de equilibrio desde `start_jd` (UT) durante `duration_days`,
    cada `step_minutes` (longitud positiva al este)."""
    count = int(round(duration_days * 1440 / step_minutes))
    jd = start_jd + np.arange(count, dtype=float) * (step_minutes / 1440)
    moon, sun, total = _state(jd, latitude_deg, longitude_deg)
    return TideSeries(
        times=[datetime_from_julian_day(float(x)) for x in jd],
        moon_m=[float(x) for x in moon],
        sun_m=[float(x) for x in sun],
        total_m=[float(x) for x in total],
    )


def day_tide_series(
    day: date, latitude_deg: float, longitude_deg: float, step_minutes: float = 10.0
) -> TideSeries:
    """Marea de equilibrio durante el día solar local `day`."""
    return tide_series(
        local_day_start_jd(day, longitude_deg), 1.0, latitude_deg, longitude_deg, step_minutes
    )


def tide_extremes(
    start_jd: float,
    duration_days: float,
    latitude_deg: float,
    longitude_deg: float,
) -> list[TideExtreme]:
    """Pleamares y bajamares de equilibrio en el intervalo.

    Se buscan los extremos locales de la serie muestreada cada 10 minutos
    y se afina cada uno por interpolación parabólica de tres puntos.
    """
    step_minutes = 10.0
    # Un paso extra a cada lado para decidir los extremos de los bordes.
    series = tide_series(
        start_jd - step_minutes / 1440,
        duration_days + 2 * step_minutes / 1440,
        latitude_deg,
        longitude_deg,
        step_minutes,
    )
    jd0 = start_jd - step_minutes / 1440
    heights = np.array(series.total_m)
    extremes: list[TideExtreme] = []
    for i in range(1, len(heights) - 1):
        left, centre, right = heights[i - 1], heights[i], heights[i + 1]
        is_high = centre > left and centre >= right
        is_low = centre < left and centre <= right
        if not (is_high or is_low):
            continue
        denominator = left - 2 * centre + right
        shift = 0.5 * (left - right) / denominator if denominator != 0 else 0.0
        peak = centre - 0.25 * (left - right) * shift
        jd = jd0 + (i + shift) * step_minutes / 1440
        if start_jd <= jd < start_jd + duration_days:
            extremes.append(TideExtreme(datetime_from_julian_day(jd), float(peak), bool(is_high)))
    return extremes


def spring_neap_ratio(jd_ut: float) -> float:
    """Cociente entre la fuerza de marea combinada de Sol y Luna y la de la
    Luna sola, en un instante, para la geometría de la fase: 1 + k·cos(2D)
    con k = relación Sol/Luna (~0.46), D la elongación de la Luna al Sol.
    Máximo (~1.46) en sicigias (nueva y llena), mínimo (~0.54) en cuadraturas.
    """
    t = julian_century_tt(jd_ut)
    moon = apparent_position(t)
    sun_longitude = float(np.radians(apparent_longitude(t)))
    elongation = float(np.radians(moon.longitude)) - sun_longitude
    solar_to_lunar = (
        SUN_TO_EARTH_MASS
        / MOON_TO_EARTH_MASS
        * (float(moon.distance_km) / (float(radius_vector(t)) * ASTRONOMICAL_UNIT_KM)) ** 3
    )
    return float(1 + solar_to_lunar * np.cos(2 * elongation))
