"""Posición de la Luna, iluminación y eventos diarios.

- Posición geocéntrica (Meeus cap. 47): longitud, latitud y distancia a
  partir de las series periódicas de `app.solar.moon_terms` (versión
  truncada de ELP-2000/82; error de ~10" en longitud y ~4" en latitud).
- Coordenadas ecuatoriales aparentes (con nutación) y paralaje.
- Fracción iluminada, ángulo de fase y ángulo de posición del limbo
  brillante (Meeus cap. 48, método de alta precisión).
- Salida, tránsito y puesta de la Luna en un día solar local (Meeus
  cap. 15, con la altitud h0 que incluye el paralaje de la Luna).

Como el resto del motor, las funciones de posición aceptan `t` (siglos
julianos desde J2000.0 en TT) como float o array de numpy y vectorizan
solas. Las que reciben un JD lo reciben en UT y le suman ΔT por dentro.
"""

from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
from numpy.typing import ArrayLike, NDArray

from app.solar.coordinates import (
    apparent_longitude,
    declination,
    radius_vector,
    right_ascension,
)
from app.solar.events import local_day_start_jd
from app.solar.horizontal import altitude, azimuth, hour_angle, local_sidereal_time, wrap180
from app.solar.moon_terms import LATITUDE_TERMS, LONGITUDE_DISTANCE_TERMS
from app.solar.nutation import nutation_in_longitude, true_obliquity
from app.solar.time import apparent_sidereal_time, datetime_from_julian_day, julian_century_tt

EARTH_EQUATORIAL_RADIUS_KM = 6378.14
"""Radio ecuatorial terrestre usado por Meeus para el paralaje lunar."""

ASTRONOMICAL_UNIT_KM = 149_597_870.7

_LONGITUDE_DISTANCE = np.array(LONGITUDE_DISTANCE_TERMS, dtype=float)
_LATITUDE = np.array(LATITUDE_TERMS, dtype=float)

Array = float | NDArray[np.floating]


@dataclass(frozen=True)
class MoonPosition:
    """Posición geocéntrica aparente de la Luna.

    Longitud y latitud eclípticas (con nutación en longitud), ascensión
    recta y declinación aparentes, todo en grados, y la distancia al centro
    de la Tierra en km. Los campos son floats o arrays de numpy según `t`.
    """

    longitude: Array
    latitude: Array
    right_ascension: Array
    declination: Array
    distance_km: Array


def mean_elements(t: ArrayLike) -> tuple[Array, Array, Array, Array, Array]:
    """Argumentos medios (Meeus cap. 47), en grados: longitud media de la
    Luna (L'), elongación media (D), anomalía media del Sol (M), anomalía
    media de la Luna (M') y argumento de latitud (F)."""
    t = np.asarray(t, dtype=float)
    lp = 218.3164477 + t * (481267.88123421 + t * (-0.0015786 + t * (1 / 538841 - t / 65194000)))
    d = 297.8501921 + t * (445267.1114034 + t * (-0.0018819 + t * (1 / 545868 - t / 113065000)))
    m = 357.5291092 + t * (35999.0502909 + t * (-0.0001536 + t / 24490000))
    mp = 134.9633964 + t * (477198.8675055 + t * (0.0087414 + t * (1 / 69699 - t / 14712000)))
    f = 93.2720950 + t * (483202.0175233 + t * (-0.0036539 + t * (-1 / 3526000 + t / 863310000)))
    return lp % 360, d % 360, m % 360, mp % 360, f % 360


def geocentric_ecliptic(t: ArrayLike) -> tuple[Array, Array, Array]:
    """Longitud, latitud (grados, equinoccio medio de la fecha) y distancia
    (km) geocéntricas de la Luna (Meeus cap. 47). La longitud no incluye la
    nutación; ver `apparent_position`."""
    t = np.asarray(t, dtype=float)
    scalar = t.ndim == 0
    t = np.atleast_1d(t)

    lp, d, m, mp, f = (np.radians(x)[None, :] for x in mean_elements(t))
    a1 = np.radians(119.75 + 131.849 * t)
    a2 = np.radians(53.09 + 479264.290 * t)
    a3 = np.radians(313.45 + 481266.484 * t)
    e = 1 - 0.002516 * t - 0.0000074 * t**2

    def arguments(table: NDArray[np.floating]) -> NDArray[np.floating]:
        return table[:, 0:1] * d + table[:, 1:2] * m + table[:, 2:3] * mp + table[:, 3:4] * f

    def eccentricity_factor(table: NDArray[np.floating]) -> NDArray[np.floating]:
        # Los términos con la anomalía del Sol se multiplican por E (|M| = 1)
        # o E^2 (|M| = 2), porque la excentricidad de la órbita terrestre
        # varía con el tiempo.
        return e[None, :] ** np.abs(table[:, 1:2])

    arg_l = arguments(_LONGITUDE_DISTANCE)
    weight_l = eccentricity_factor(_LONGITUDE_DISTANCE)
    sum_l = np.sum(_LONGITUDE_DISTANCE[:, 4:5] * weight_l * np.sin(arg_l), axis=0)
    sum_r = np.sum(_LONGITUDE_DISTANCE[:, 5:6] * weight_l * np.cos(arg_l), axis=0)

    arg_b = arguments(_LATITUDE)
    sum_b = np.sum(_LATITUDE[:, 4:5] * eccentricity_factor(_LATITUDE) * np.sin(arg_b), axis=0)

    # Términos aditivos: acción de Venus (A1), de Júpiter (A2) y el
    # aplastamiento terrestre (L', F, A3).
    lp_rad = lp[0]
    f_rad = f[0]
    mp_rad = mp[0]
    sum_l += 3958 * np.sin(a1) + 1962 * np.sin(lp_rad - f_rad) + 318 * np.sin(a2)
    sum_b += (
        -2235 * np.sin(lp_rad)
        + 382 * np.sin(a3)
        + 175 * np.sin(a1 - f_rad)
        + 175 * np.sin(a1 + f_rad)
        + 127 * np.sin(lp_rad - mp_rad)
        - 115 * np.sin(lp_rad + mp_rad)
    )

    longitude = (np.degrees(lp_rad) + sum_l / 1e6) % 360
    latitude = sum_b / 1e6
    distance = 385000.56 + sum_r / 1000
    if scalar:
        return float(longitude[0]), float(latitude[0]), float(distance[0])
    return longitude, latitude, distance


def ecliptic_to_equatorial(
    longitude_deg: ArrayLike, latitude_deg: ArrayLike, obliquity_deg: ArrayLike
) -> tuple[Array, Array]:
    """Longitud y latitud eclípticas a ascensión recta y declinación (Meeus
    cap. 13), en grados; α en [0, 360)."""
    lam = np.radians(longitude_deg)
    beta = np.radians(latitude_deg)
    eps = np.radians(obliquity_deg)
    alpha = np.arctan2(np.sin(lam) * np.cos(eps) - np.tan(beta) * np.sin(eps), np.cos(lam))
    delta = np.arcsin(np.sin(beta) * np.cos(eps) + np.cos(beta) * np.sin(eps) * np.sin(lam))
    return np.degrees(alpha) % 360, np.degrees(delta)


def apparent_position(t: ArrayLike) -> MoonPosition:
    """Posición geocéntrica aparente de la Luna en `t` (siglos julianos en
    TT): coordenadas eclípticas con nutación y ecuatoriales aparentes."""
    longitude, latitude, distance = geocentric_ecliptic(t)
    longitude = (longitude + nutation_in_longitude(t)) % 360
    alpha, delta = ecliptic_to_equatorial(longitude, latitude, true_obliquity(t))
    return MoonPosition(longitude, latitude, alpha, delta, distance)


def horizontal_parallax(distance_km: ArrayLike) -> Array:
    """Paralaje horizontal ecuatorial de la Luna (π), en grados, a la
    distancia dada (Meeus cap. 47: sin π = 6378.14 / Δ)."""
    return np.degrees(np.arcsin(EARTH_EQUATORIAL_RADIUS_KM / np.asarray(distance_km)))


def topocentric_equatorial(
    right_ascension_deg: ArrayLike,
    declination_deg: ArrayLike,
    distance_km: ArrayLike,
    hour_angle_deg: ArrayLike,
    latitude_deg: float,
    elevation_m: float = 0.0,
) -> tuple[Array, Array, Array]:
    """Corrección por paralaje (Meeus cap. 40): ascensión recta,
    declinación y ángulo horario topocéntricos, en grados, para un
    observador en la superficie. Hasta ~1° de diferencia para la Luna."""
    pi = np.radians(horizontal_parallax(distance_km))
    phi = np.radians(latitude_deg)
    u = np.arctan(0.99664719 * np.tan(phi))
    rho_sin = 0.99664719 * np.sin(u) + elevation_m / 6378140 * np.sin(phi)
    rho_cos = np.cos(u) + elevation_m / 6378140 * np.cos(phi)

    h = np.radians(hour_angle_deg)
    delta = np.radians(declination_deg)
    denominator = np.cos(delta) - rho_cos * np.sin(pi) * np.cos(h)
    d_alpha = np.arctan2(-rho_cos * np.sin(pi) * np.sin(h), denominator)
    delta_topo = np.arctan2((np.sin(delta) - rho_sin * np.sin(pi)) * np.cos(d_alpha), denominator)
    d_alpha_deg = np.degrees(d_alpha)
    return (
        (np.asarray(right_ascension_deg) + d_alpha_deg) % 360,
        np.degrees(delta_topo),
        np.asarray(hour_angle_deg) - d_alpha_deg,
    )


@dataclass(frozen=True)
class Illumination:
    """Iluminación de la Luna vista desde la Tierra.

    `fraction` es la fracción del disco iluminada (0 = nueva, 1 = llena);
    `phase_angle_deg` es el ángulo de fase i (180° = nueva, 0° = llena);
    `elongation_deg` es la elongación geocéntrica de la Luna al Sol (0 a 180°)
    y `ecliptic_elongation_deg` la diferencia de longitudes eclípticas
    Luna - Sol, en [0, 360): 0° nueva, 90° cuarto creciente, 180° llena,
    270° cuarto menguante;
    `bright_limb_angle_deg` es el ángulo de posición del punto medio del
    limbo brillante, desde el norte celeste hacia el este; `waxing` dice si
    la Luna está creciente (la iluminación aumenta).
    """

    fraction: float
    phase_angle_deg: float
    elongation_deg: float
    ecliptic_elongation_deg: float
    bright_limb_angle_deg: float
    waxing: bool

    @property
    def phase_key(self) -> str:
        """Nombre de la fase en 8 octantes centrados en 0°, 45°, ...: uno de
        `PHASE_KEYS` ("new", "waxing_crescent", "first_quarter",
        "waxing_gibbous", "full", "waning_gibbous", "last_quarter",
        "waning_crescent")."""
        return PHASE_KEYS[int(((self.ecliptic_elongation_deg + 22.5) % 360) // 45)]


def illumination(jd_ut: float) -> Illumination:
    """Iluminación de la Luna en el instante `jd_ut` (Meeus cap. 48, método
    de alta precisión con las posiciones geocéntricas de la Luna y el Sol)."""
    t = julian_century_tt(jd_ut)
    moon = apparent_position(t)
    sun_lambda = float(apparent_longitude(t))
    sun_alpha = float(right_ascension(t))
    sun_delta = float(declination(t))
    sun_distance_km = float(radius_vector(t)) * ASTRONOMICAL_UNIT_KM

    # Elongación geocéntrica ψ del Sol a la Luna.
    moon_alpha, moon_delta = np.radians(moon.right_ascension), np.radians(moon.declination)
    sa, sd = np.radians(sun_alpha), np.radians(sun_delta)
    cos_psi = np.sin(sd) * np.sin(moon_delta) + np.cos(sd) * np.cos(moon_delta) * np.cos(
        sa - moon_alpha
    )
    psi = float(np.arccos(np.clip(cos_psi, -1.0, 1.0)))
    phase_angle = np.arctan2(
        sun_distance_km * np.sin(psi), moon.distance_km - sun_distance_km * np.cos(psi)
    )

    # Ángulo de posición del limbo brillante.
    chi = np.arctan2(
        np.cos(sd) * np.sin(sa - moon_alpha),
        np.sin(sd) * np.cos(moon_delta) - np.cos(sd) * np.sin(moon_delta) * np.cos(sa - moon_alpha),
    )
    # Creciente: la Luna está al este del Sol (longitud mayor, hasta 180°).
    ecliptic_elongation = (float(moon.longitude) - sun_lambda) % 360
    waxing = bool(ecliptic_elongation < 180)
    return Illumination(
        fraction=float((1 + np.cos(phase_angle)) / 2),
        phase_angle_deg=float(np.degrees(phase_angle)),
        elongation_deg=float(np.degrees(psi)),
        ecliptic_elongation_deg=ecliptic_elongation,
        bright_limb_angle_deg=float(np.degrees(chi) % 360),
        waxing=waxing,
    )


@dataclass(frozen=True)
class MoonDay:
    """Eventos de la Luna en un día solar local, en UT.

    A diferencia del Sol, la Luna sale unos 50 minutos más tarde cada día,
    así que algún día del mes no sale (o no se pone) dentro del día local:
    el evento correspondiente es `None`. `always_above` solo se informa
    cuando no hay salida ni puesta en el día (Luna circumpolar o siempre
    bajo el horizonte, en latitudes altas).
    """

    rise: datetime | None
    transit: datetime | None
    set: datetime | None
    transit_altitude_deg: float | None
    always_above: bool | None


@dataclass(frozen=True)
class MoonTrajectory:
    """Altitud y azimut de la Luna (topocéntricos, sin refracción) en
    instantes equiespaciados a lo largo del día solar local."""

    times: list[datetime]
    altitude: list[float]
    azimuth: list[float]
    illuminated_fraction: float


PHASE_KEYS = (
    "new",
    "waxing_crescent",
    "first_quarter",
    "waxing_gibbous",
    "full",
    "waning_gibbous",
    "last_quarter",
    "waning_crescent",
)

_SCAN_STEP_MINUTES = 10
_BISECTION_STEPS = 30


def _horizon_altitude_deg(parallax_deg: ArrayLike) -> Array:
    """Altitud geocéntrica del centro de la Luna a la salida/puesta
    (Meeus cap. 15): 0.7275 π - 0.5667°, donde 0.5667° (34') es la
    refracción en el horizonte y 0.7275 π incluye el semidiámetro lunar
    (con π, el paralaje horizontal)."""
    return 0.7275 * np.asarray(parallax_deg) - 0.5667


def _geocentric_state(jd: ArrayLike, latitude_deg: float, longitude_deg: float):
    """Altitud geocéntrica, ángulo horario (-180, 180] y h0 de la Luna en
    los instantes `jd` (UT) para el observador dado."""
    jd = np.asarray(jd, dtype=float)
    t = julian_century_tt(jd)
    position = apparent_position(t)
    lst = local_sidereal_time(apparent_sidereal_time(jd), longitude_deg)
    h = hour_angle(lst, position.right_ascension)
    alt = altitude(latitude_deg, position.declination, h)
    h0 = _horizon_altitude_deg(horizontal_parallax(position.distance_km))
    return alt, h, h0


def _bisect(fn, low: float, high: float) -> float:
    """Raíz de `fn` en [low, high] por bisección, dado que cambia de signo."""
    f_low = fn(low)
    for _ in range(_BISECTION_STEPS):
        mid = (low + high) / 2
        f_mid = fn(mid)
        if (f_mid > 0) == (f_low > 0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return (low + high) / 2


def moon_day(day: date, latitude_deg: float, longitude_deg: float) -> MoonDay:
    """Salida, tránsito y puesta de la Luna en el día solar local `day`
    (de una medianoche media local a la siguiente), para el observador
    dado (longitud positiva al este).

    Se explora la altitud cada 10 minutos y cada cambio de signo se afina
    por bisección: es más robusto que la iteración de Meeus para una Luna
    que se mueve ~13°/día y que algunos días no sale o no se pone.
    """
    start = local_day_start_jd(day, longitude_deg)
    steps = 24 * 60 // _SCAN_STEP_MINUTES
    grid = start + np.arange(steps + 1) / steps

    alt, h, h0 = _geocentric_state(grid, latitude_deg, longitude_deg)
    above = alt - h0

    def rel_altitude(jd: float) -> float:
        a, _, h0_now = _geocentric_state(jd, latitude_deg, longitude_deg)
        return float(a - h0_now)

    def rel_hour_angle(jd: float) -> float:
        return float(_geocentric_state(jd, latitude_deg, longitude_deg)[1])

    rise = sets = transit = None
    for i in range(steps):
        if above[i] < 0 <= above[i + 1] and rise is None:
            rise = _bisect(rel_altitude, grid[i], grid[i + 1])
        elif above[i] >= 0 > above[i + 1] and sets is None:
            sets = _bisect(rel_altitude, grid[i], grid[i + 1])
        # Tránsito superior: el ángulo horario pasa de negativo a positivo
        # (el salto de +180 a -180 del tránsito inferior se descarta).
        if h[i] < 0 <= h[i + 1] and h[i + 1] - h[i] < 90 and transit is None:
            transit = _bisect(rel_hour_angle, grid[i], grid[i + 1])

    transit_altitude = None
    if transit is not None:
        transit_alt, _, _ = _geocentric_state(transit, latitude_deg, longitude_deg)
        transit_altitude = float(transit_alt)

    always_above = None
    if rise is None and sets is None:
        always_above = bool(above[0] >= 0)

    def to_datetime(jd: float | None) -> datetime | None:
        return None if jd is None else datetime_from_julian_day(jd)

    return MoonDay(
        rise=to_datetime(rise),
        transit=to_datetime(transit),
        set=to_datetime(sets),
        transit_altitude_deg=transit_altitude,
        always_above=always_above,
    )


def moon_trajectory(
    day: date,
    latitude_deg: float,
    longitude_deg: float,
    num_samples: int = 96,
    elevation_m: float = 0.0,
) -> MoonTrajectory:
    """Altitud y azimut topocéntricos (con paralaje, sin refracción) de la
    Luna en `num_samples` instantes del día solar local `day`, y la fracción
    iluminada al mediodía local."""
    start = local_day_start_jd(day, longitude_deg)
    jd = start + np.arange(num_samples, dtype=float) / num_samples

    t = julian_century_tt(jd)
    position = apparent_position(t)
    lst = local_sidereal_time(apparent_sidereal_time(jd), longitude_deg)
    h = hour_angle(lst, position.right_ascension)
    _, delta_topo, h_topo = topocentric_equatorial(
        position.right_ascension,
        position.declination,
        position.distance_km,
        h,
        latitude_deg,
        elevation_m,
    )
    h_topo = wrap180(h_topo)
    return MoonTrajectory(
        times=[datetime_from_julian_day(float(x)) for x in jd],
        altitude=[float(x) for x in altitude(latitude_deg, delta_topo, h_topo)],
        azimuth=[float(x) for x in azimuth(latitude_deg, delta_topo, h_topo)],
        illuminated_fraction=illumination(start + 0.5).fraction,
    )


def moon_altitude(
    jd_ut: float, latitude_deg: float, longitude_deg: float, elevation_m: float = 0.0
) -> float:
    """Altitud topocéntrica (con paralaje, sin refracción) de la Luna en el
    instante `jd_ut`, en grados. Positiva: la Luna está sobre el horizonte."""
    t = julian_century_tt(jd_ut)
    position = apparent_position(t)
    lst = local_sidereal_time(apparent_sidereal_time(jd_ut), longitude_deg)
    h = hour_angle(lst, position.right_ascension)
    _, delta_topo, h_topo = topocentric_equatorial(
        position.right_ascension,
        position.declination,
        position.distance_km,
        h,
        latitude_deg,
        elevation_m,
    )
    return float(altitude(latitude_deg, delta_topo, wrap180(h_topo)))
