"""Orto, tránsito y ocaso del Sol (Meeus cap. 15).

Simplificación respecto al algoritmo del libro: Meeus interpola α/δ a
partir de tres muestras diarias (día anterior/actual/siguiente) porque
parte de tablas de efemérides discretas. Acá `app.solar.coordinates` es
continuo en T, así que en cada iteración evaluamos directamente la
posición solar en el instante exacto — la interpolación de 3 puntos del
libro queda innecesaria.

La posición del Sol se evalúa en TT (se suma ΔT al instante en UT, ver
`app.solar.time.julian_century_tt`) y el ángulo horario usa el tiempo
sidéreo aparente (con la ecuación de los equinoccios).

El instante de cruce de una altitud no se busca con el método de Newton
sobre la altitud (que divide por sin H y se vuelve inestable cuando el Sol
apenas roza el umbral, en los días límite de latitudes altas), sino
iterando sobre el ángulo horario: en cada paso se calcula el semiarco
diurno H0 con la declinación de ese instante y se corrige el instante por
la diferencia entre el ángulo horario actual y ±H0. Es la misma condición
(cos H0 = (sin h0 - sin φ sin δ) / (cos φ cos δ)), pero sin división por
cero y con la diferencia angular acotada a (-180, 180].

Convención de longitud: positiva al este (a diferencia del propio libro de
Meeus, que la toma positiva al oeste), por ser la convención moderna más
intuitiva (coincide, por ejemplo, con la de coordenadas GPS).

Vectorización: `_solar_transit_jd`, `_hour_angle_at_altitude` y
`_refine_horizon_crossing` operan con `numpy` y no con ramas de Python
(`if`/`return None`), así que funcionan igual con un `jd0` escalar (un
día — usado por `solar_transit`/`sunrise_sunset`) o con un array de numpy
(todos los días de un año a la vez — usado por `sunrise_sunset_year`, base
del endpoint `GET /sol/anual`). Es el mismo cálculo en los dos casos: no
hay una versión "vectorizada" separada de la versión "de un día".
"""

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np

from app.solar.coordinates import declination, radius_vector, right_ascension
from app.solar.horizontal import altitude, azimuth, hour_angle, local_sidereal_time, wrap180
from app.solar.irradiance import DEFAULT_LINKE_TURBIDITY, clear_sky_components
from app.solar.refraction import apparent_altitude as refracted_altitude
from app.solar.time import (
    apparent_sidereal_time,
    datetime_from_julian_day,
    julian_century_tt,
    julian_day,
)

STANDARD_ALTITUDE_SUN = -0.8333
"""h0: altitud aparente estándar de orto/ocaso del Sol, en grados (Meeus
cap. 15) — incluye la refracción atmosférica típica en el horizonte (~34')
y el semidiámetro solar (~16'), no la posición geométrica exacta."""

_MAX_ITERATIONS = 5


@dataclass(frozen=True)
class SunDay:
    """Eventos solares de un día para un observador dado, en UT.

    `sunrise`/`sunset` son `None` cuando el Sol no cruza `altitude_deg` ese
    día; en ese caso `always_above` indica si quedó todo el día por encima
    (sol de medianoche) o por debajo (noche polar) de esa altitud.
    """

    transit: datetime
    sunrise: datetime | None
    sunset: datetime | None
    always_above: bool | None


@dataclass(frozen=True)
class SunTrajectory:
    """Trayectoria del Sol (altitud y azimut) a lo largo de un día,
    muestreada en instantes UT equiespaciados — base del gráfico polar del
    punto 3 (trayectoria/posición del Sol).

    `altitude` es la altitud verdadera (geométrica, sin refracción);
    `apparent_altitude` es la que realmente se vería (con la corrección de
    `app.solar.refraction` — más notoria cerca del horizonte). `times`
    cubre exactamente las 24h del día solar local (ver `local_day_start_jd`:
    el primer instante es la medianoche media local; el último, un paso de
    muestreo antes de la siguiente, sin repetirla)."""

    times: list[datetime]
    altitude: list[float]
    apparent_altitude: list[float]
    azimuth: list[float]


@dataclass(frozen=True)
class SolarNoon:
    """Mediodía solar (tránsito) y la inclinación del Sol en ese instante
    — punto 4 del plan técnico.

    `altitude_deg` es la altitud verdadera máxima del día (H=0 por
    definición de tránsito); `apparent_altitude_deg` es la que realmente
    se vería (corrección de `app.solar.refraction`). `azimuth_deg` es 0°
    (Norte) o 180° (Sur) salvo en el caso límite en que el Sol pasa
    exactamente por el cenit (ver `app.solar.horizontal.azimuth`)."""

    transit: datetime
    altitude_deg: float
    apparent_altitude_deg: float
    azimuth_deg: float


@dataclass(frozen=True)
class SunYear:
    """Eventos solares de todos los días de un año calendario, para un
    observador dado — la versión vectorizada de `SunDay` que usa el
    endpoint `GET /sol/anual`. Cada lista tiene un elemento por día del
    año, en el mismo orden que `dates`."""

    dates: list[date]
    transit: list[datetime]
    sunrise: list[datetime | None]
    sunset: list[datetime | None]
    always_above: list[bool | None]


@dataclass(frozen=True)
class DailyIrradiation:
    """Irradiancia solar (cielo despejado) sobre una superficie horizontal a
    lo largo de un día y su integral — energía recibida por m² en el día.
    Punto 5 del plan técnico, endpoint `GET /sol/irradiancia`.

    `power_w_per_m2` es la irradiancia global horizontal (directa +
    difusa); `direct_w_per_m2` y `diffuse_w_per_m2` son sus dos
    componentes. Las energías son la integral de cada serie en el día.
    """

    times: list[datetime]
    power_w_per_m2: list[float]
    direct_w_per_m2: list[float]
    diffuse_w_per_m2: list[float]
    energy_wh_per_m2: float
    direct_energy_wh_per_m2: float
    diffuse_energy_wh_per_m2: float


def local_day_start_jd(day: date, longitude_deg: float) -> float:
    """JD (UT) de la medianoche media local de `day` en la longitud dada
    (positiva al este): 0h UT menos longitud/360 días.

    Las series muestreadas a lo largo de un día (trayectoria, irradiancia,
    panel) parten de acá y no de 0h UT: a longitudes lejanas a Greenwich el
    día solar local queda a caballo de dos días UT (ej. el amanecer en
    Sídney ocurre el día UT anterior), y una ventana de 24h desde 0h UT
    cortaría las horas de luz.
    """
    return julian_day(datetime(day.year, day.month, day.day, tzinfo=UTC)) - longitude_deg / 360


def _sun_hour_angle(jd, longitude_deg):
    """Ángulo horario (H) del Sol en `jd`, en grados, normalizado a
    (-180, 180]. Positivo del mediodía solar hacia adelante (tarde).

    `jd` puede ser un float o un array de numpy."""
    t = julian_century_tt(jd)
    alpha = right_ascension(t)
    lst = local_sidereal_time(apparent_sidereal_time(jd), longitude_deg)
    return hour_angle(lst, alpha)


def _hour_angle_at_altitude(latitude_deg, declination_deg, altitude_deg):
    """H0 (grados): semiarco diurno al que el Sol cruza `altitude_deg` para
    la latitud y declinación dadas, y las máscaras de los casos límite en
    que no la cruza ese día.

    `declination_deg` puede ser un float o un array de numpy. Devuelve
    `(h0, always_above, always_below)`: `h0` siempre queda acotado a
    [0, 180] (no debe usarse donde `always_above`/`always_below` sean
    verdaderos — el Sol no cruza `altitude_deg` ese día: circumpolar,
    siempre por encima, o nunca visible, siempre por debajo).
    """
    phi = np.radians(latitude_deg)
    delta = np.radians(declination_deg)
    cos_h0 = (np.sin(np.radians(altitude_deg)) - np.sin(phi) * np.sin(delta)) / (
        np.cos(phi) * np.cos(delta)
    )
    always_above = cos_h0 < -1.0
    always_below = cos_h0 > 1.0
    h0 = np.degrees(np.arccos(np.clip(cos_h0, -1.0, 1.0)))
    return h0, always_above, always_below


def _solar_transit_jd(jd0, longitude_deg):
    """JD del tránsito solar. `jd0` (JD a 0h UT) puede ser un float o un
    array de numpy."""
    m = (0.5 - longitude_deg / 360) % 1
    for _ in range(_MAX_ITERATIONS):
        m = m - _sun_hour_angle(jd0 + m, longitude_deg) / 360
    return jd0 + m


def _refine_horizon_crossing(jd0, m_initial, latitude_deg, longitude_deg, altitude_deg, sign):
    """Refina por iteración el instante (fracción de día `m` desde `jd0`)
    en que el Sol cruza `altitude_deg` y devuelve el JD resultante.

    `sign` es -1 para la salida (ángulo horario -H0) y +1 para la puesta
    (+H0). `jd0`/`m_initial` pueden ser floats o arrays de numpy. En los
    días límite (circumpolares) el resultado no tiene sentido y quien llama
    lo descarta; igual no hay divisiones por cero ni NaN, porque H0 sale
    acotado a [0, 180].
    """
    m = m_initial
    for _ in range(_MAX_ITERATIONS):
        jd = jd0 + m
        delta_deg = declination(julian_century_tt(jd))
        h0, _, _ = _hour_angle_at_altitude(latitude_deg, delta_deg, altitude_deg)
        error_deg = wrap180(_sun_hour_angle(jd, longitude_deg) - sign * h0)
        m = m - error_deg / 360

    return jd0 + m


def solar_transit(day: date, longitude_deg: float) -> datetime:
    """Instante (UT) del tránsito solar (mediodía solar aparente) para la
    fecha y longitud (positiva al este) dadas."""
    jd0 = julian_day(datetime(day.year, day.month, day.day, tzinfo=UTC))
    return datetime_from_julian_day(float(_solar_transit_jd(jd0, longitude_deg)))


def sunrise_sunset(
    day: date,
    latitude_deg: float,
    longitude_deg: float,
    altitude_deg: float = STANDARD_ALTITUDE_SUN,
) -> SunDay:
    """Orto y ocaso (UT) del Sol para la fecha, latitud y longitud (positiva
    al este) dadas, a la altitud aparente `altitude_deg` (por defecto,
    `STANDARD_ALTITUDE_SUN`)."""
    jd0 = julian_day(datetime(day.year, day.month, day.day, tzinfo=UTC))
    transit_jd = float(_solar_transit_jd(jd0, longitude_deg))
    transit = datetime_from_julian_day(transit_jd)
    m_transit = transit_jd - jd0

    delta_at_transit = float(declination(julian_century_tt(transit_jd)))
    h0, always_above, always_below = _hour_angle_at_altitude(
        latitude_deg, delta_at_transit, altitude_deg
    )

    if bool(always_above) or bool(always_below):
        return SunDay(transit=transit, sunrise=None, sunset=None, always_above=bool(always_above))

    h0 = float(h0)
    sunrise_jd = float(
        _refine_horizon_crossing(
            jd0, m_transit - h0 / 360, latitude_deg, longitude_deg, altitude_deg, sign=-1
        )
    )
    sunset_jd = float(
        _refine_horizon_crossing(
            jd0, m_transit + h0 / 360, latitude_deg, longitude_deg, altitude_deg, sign=1
        )
    )
    return SunDay(
        transit=transit,
        sunrise=datetime_from_julian_day(sunrise_jd),
        sunset=datetime_from_julian_day(sunset_jd),
        always_above=None,
    )


def sunrise_sunset_year(
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    altitude_deg: float = STANDARD_ALTITUDE_SUN,
) -> SunYear:
    """Igual que `sunrise_sunset`, pero para los 365/366 días de `year` a
    la vez, vectorizado con numpy: toda la cadena de cálculo
    (`coordinates.py`, `horizontal.py`, este módulo) opera sobre un array
    con un elemento por día del año en lugar de iterar día a día en Python
    puro. Base del endpoint `GET /sol/anual`."""
    days_in_year = 366 if calendar.isleap(year) else 365
    jan1 = julian_day(datetime(year, 1, 1, tzinfo=UTC))
    jd0 = jan1 + np.arange(days_in_year, dtype=float)

    transit_jd = _solar_transit_jd(jd0, longitude_deg)
    m_transit = transit_jd - jd0

    delta_at_transit = declination(julian_century_tt(transit_jd))
    h0, always_above, always_below = _hour_angle_at_altitude(
        latitude_deg, delta_at_transit, altitude_deg
    )
    polar = always_above | always_below

    sunrise_jd = _refine_horizon_crossing(
        jd0, m_transit - h0 / 360, latitude_deg, longitude_deg, altitude_deg, sign=-1
    )
    sunset_jd = _refine_horizon_crossing(
        jd0, m_transit + h0 / 360, latitude_deg, longitude_deg, altitude_deg, sign=1
    )

    # La conversión final a `datetime` es, a propósito, el único paso que
    # queda como un loop de Python: opera sobre ~365 floats ya calculados,
    # no sobre el motor de cálculo en sí (eso es lo que se vectorizó).
    dates = [date(year, 1, 1) + timedelta(days=i) for i in range(days_in_year)]
    transit = [datetime_from_julian_day(float(jd)) for jd in transit_jd]
    sunrise = [
        None if is_polar else datetime_from_julian_day(float(jd))
        for is_polar, jd in zip(polar, sunrise_jd, strict=True)
    ]
    sunset = [
        None if is_polar else datetime_from_julian_day(float(jd))
        for is_polar, jd in zip(polar, sunset_jd, strict=True)
    ]
    always_above_list = [
        bool(above) if is_polar else None
        for is_polar, above in zip(polar, always_above, strict=True)
    ]

    return SunYear(
        dates=dates,
        transit=transit,
        sunrise=sunrise,
        sunset=sunset,
        always_above=always_above_list,
    )


def sun_trajectory(
    day: date,
    latitude_deg: float,
    longitude_deg: float,
    num_samples: int = 96,
    pressure_mbar: float = 1010.0,
    temperature_c: float = 10.0,
) -> SunTrajectory:
    """Trayectoria del Sol (altitud y azimut) a lo largo del día solar local
    `day` (desde su medianoche media local, ver `local_day_start_jd`), en
    `num_samples` instantes equiespaciados (por defecto 96 = cada 15
    minutos), vectorizado con numpy. `pressure_mbar` y `temperature_c`
    ajustan la refracción de `apparent_altitude`. Base del endpoint `GET /sol/trayectoria`
    (punto 3, gráfico polar).

    No hace falta iterar como en `sunrise_sunset`/`solar_transit`: cada
    muestra es una evaluación directa e independiente de la posición solar
    en un instante conocido, así que alcanza con componer las funciones
    públicas de `coordinates.py` y `horizontal.py`.
    """
    jd = local_day_start_jd(day, longitude_deg) + np.arange(num_samples, dtype=float) / num_samples

    t = julian_century_tt(jd)
    alpha = right_ascension(t)
    delta = declination(t)
    lst = local_sidereal_time(apparent_sidereal_time(jd), longitude_deg)
    h = hour_angle(lst, alpha)

    alt = altitude(latitude_deg, delta, h)
    az = azimuth(latitude_deg, delta, h)
    apparent_alt = refracted_altitude(alt, pressure_mbar, temperature_c)

    times = [datetime_from_julian_day(float(x)) for x in jd]
    return SunTrajectory(
        times=times,
        altitude=[float(x) for x in alt],
        apparent_altitude=[float(x) for x in apparent_alt],
        azimuth=[float(x) for x in az],
    )


def solar_noon(
    day: date,
    latitude_deg: float,
    longitude_deg: float,
    pressure_mbar: float = 1010.0,
    temperature_c: float = 10.0,
) -> SolarNoon:
    """Mediodía solar aparente y la inclinación del Sol en ese instante
    (punto 4): altitud máxima del día y azimut, evaluadas en H=0 por
    definición de tránsito."""
    transit = solar_transit(day, longitude_deg)
    delta = float(declination(julian_century_tt(julian_day(transit))))
    altitude_deg = float(altitude(latitude_deg, delta, 0.0))
    return SolarNoon(
        transit=transit,
        altitude_deg=altitude_deg,
        apparent_altitude_deg=float(refracted_altitude(altitude_deg, pressure_mbar, temperature_c)),
        azimuth_deg=float(azimuth(latitude_deg, delta, 0.0)),
    )


def daily_irradiation(
    day: date,
    latitude_deg: float,
    longitude_deg: float,
    num_samples: int = 96,
    elevation_m: float = 0.0,
    linke_turbidity: float = DEFAULT_LINKE_TURBIDITY,
) -> DailyIrradiation:
    """Irradiancia solar (cielo despejado, `app.solar.irradiance`)
    muestreada a lo largo del día solar local `day`, y la energía recibida
    por m² en el día (regla del trapecio sobre las muestras, cerrando el día
    a las 24h). Punto 5, endpoint `GET /sol/irradiancia`.

    Reusa `sun_trajectory` para la altitud en cada muestra (mismos
    instantes) y solo agrega el radio vector Tierra-Sol, que es lo único
    que le falta a `irradiance.clear_sky_components`.
    """
    trajectory = sun_trajectory(day, latitude_deg, longitude_deg, num_samples)

    jd = local_day_start_jd(day, longitude_deg) + np.arange(num_samples, dtype=float) / num_samples
    r = radius_vector(julian_century_tt(jd))
    altitude_deg = np.array(trajectory.altitude)
    dni, dhi, ghi = clear_sky_components(altitude_deg, r, elevation_m, linke_turbidity)
    direct_horizontal = dni * np.sin(np.radians(np.clip(altitude_deg, 0.0, None)))

    # Regla del trapecio sobre las 24h, cerrando el ciclo con una muestra
    # más a las 24h (prácticamente igual a la de las 0h: el cambio
    # orbital/de declinación en un día es despreciable a esta precisión).
    hours = np.append(np.arange(num_samples, dtype=float) * (24 / num_samples), 24.0)

    def energy_wh(power: np.ndarray) -> float:
        return float(np.trapezoid(np.append(power, power[0]), hours))

    return DailyIrradiation(
        times=trajectory.times,
        power_w_per_m2=[float(x) for x in ghi],
        direct_w_per_m2=[float(x) for x in direct_horizontal],
        diffuse_w_per_m2=[float(x) for x in dhi],
        energy_wh_per_m2=energy_wh(ghi),
        direct_energy_wh_per_m2=energy_wh(direct_horizontal),
        diffuse_energy_wh_per_m2=energy_wh(dhi),
    )
