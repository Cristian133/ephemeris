"""Tiempo: Día Juliano (JD) y siglos julianos desde J2000.0.

Toda la app calcula internamente en Tiempo Universal (UT); la conversión a
hora local del observador se hace en la capa de presentación (ver
docs/plan_tecnico.md, sección 4.1).

Calendario: los `datetime` de Python son gregorianos prolépticos, así que
`julian_day` y `datetime_from_julian_day` también lo son en todo el rango
(consistentes entre sí y con ISO 8601). El calendario histórico (juliano
antes de 1582-10-15, como lo usa Meeus) está en `julian_day_from_calendar` y
`calendar_from_julian_day`, que trabajan con tuplas (año, mes, día) y no con
`datetime` justamente para no mezclar los dos calendarios en un mismo tipo.

Escalas de tiempo: las posiciones astronómicas se evalúan en TT (tiempo
terrestre) y la rotación de la Tierra (ángulo horario) en UT. `delta_t` da
la diferencia TT - UT; `julian_century_tt` convierte un JD en UT al `t` en
TT que esperan las funciones de `app.solar.coordinates`.
"""

import math
from datetime import UTC, datetime, timedelta

import numpy as np
from numpy.typing import ArrayLike

from app.solar.nutation import equation_of_equinoxes

J2000 = 2451545.0
"""JD de la época estándar J2000.0 (2000-01-01 12:00 UT)."""

_DAYS_PER_JULIAN_CENTURY = 36525.0


def julian_day(moment: datetime) -> float:
    """Convierte un instante a Día Juliano (JD).

    `moment` puede ser naive (se asume ya en UT) o timezone-aware (se
    convierte a UT antes de calcular).
    """
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC).replace(tzinfo=None)

    year, month = moment.year, moment.month
    day = (
        moment.day
        + moment.hour / 24
        + moment.minute / 1_440
        + (moment.second + moment.microsecond / 1e6) / 86_400
    )

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + a // 4

    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5


def julian_century(jd: float) -> float:
    """Siglos julianos transcurridos desde J2000.0 (T)."""
    return (jd - J2000) / _DAYS_PER_JULIAN_CENTURY


def julian_day_from_calendar(year: int, month: int, day: float, calendar: str = "auto") -> float:
    """Día Juliano de una fecha de calendario (Meeus cap. 7).

    `calendar`: "gregorian", "julian" o "auto" (juliano hasta el 4 de
    octubre de 1582 inclusive, gregoriano desde el 15 de octubre de 1582,
    como la reforma). `day` puede tener parte fraccionaria (hora del día).
    Las fechas del salto de la reforma (5 a 14 de octubre de 1582) no
    existen y levantan `ValueError` en modo "auto".
    """
    if calendar not in ("auto", "gregorian", "julian"):
        raise ValueError(f"calendar inválido: {calendar!r}")
    if calendar == "auto":
        if (year, month, math.floor(day)) >= (1582, 10, 15):
            calendar = "gregorian"
        elif (year, month, math.floor(day)) <= (1582, 10, 4):
            calendar = "julian"
        else:
            raise ValueError("el 5 al 14 de octubre de 1582 no existen en ningún calendario")

    if month <= 2:
        year -= 1
        month += 12
    b = 0
    if calendar == "gregorian":
        a = year // 100
        b = 2 - a + a // 4
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5


def calendar_from_julian_day(jd: float, calendar: str = "auto") -> tuple[int, int, float, str]:
    """Fecha de calendario (año, mes, día con fracción, calendario usado) de
    un Día Juliano (Meeus cap. 7). Inversa de `julian_day_from_calendar`.

    En modo "auto" usa el calendario juliano para JD < 2299160.5 (antes del
    15 de octubre de 1582) y el gregoriano desde ahí. Solo válido para
    JD >= 0.
    """
    if calendar not in ("auto", "gregorian", "julian"):
        raise ValueError(f"calendar inválido: {calendar!r}")
    if jd < 0:
        raise ValueError("jd debe ser >= 0")
    if calendar == "auto":
        calendar = "gregorian" if jd >= 2299160.5 else "julian"

    jd_shifted = jd + 0.5
    z = math.floor(jd_shifted)
    f = jd_shifted - z
    if calendar == "gregorian":
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    else:
        a = z

    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)

    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return year, month, day, calendar


def datetime_from_julian_day(jd: float) -> datetime:
    """Convierte un Día Juliano (JD) a un instante UTC.

    Inversa de `julian_day` (Meeus cap. 7): como esa función, asume
    calendario gregoriano proléptico en todo el rango de fechas (sin la
    rama juliana previa a 1582 del algoritmo original del libro), para que
    el redondeo de ambas funciones sea consistente entre sí.
    """
    jd_shifted = jd + 0.5
    z = math.floor(jd_shifted)
    f = jd_shifted - z

    # INT() en Meeus es floor (mayor entero <= x), no truncamiento — importa
    # para fechas donde estos cocientes dan negativo.
    alpha = math.floor((z - 1867216.25) / 36524.25)
    a = z + 1 + alpha - alpha // 4

    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)

    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715

    day_int = int(day)
    seconds_into_day = round((day - day_int) * 86_400)
    return datetime(year, month, day_int, tzinfo=UTC) + timedelta(seconds=seconds_into_day)


def mean_sidereal_time(jd: float) -> float:
    """Tiempo sidéreo medio en Greenwich (θ0), en grados, normalizado a
    [0, 360) (Meeus cap. 12, ecuación 12.4).

    Válido para cualquier instante `jd`, no solo 0h UT. No incluye la
    ecuación de los equinoccios (corrección por nutación): la diferencia
    con el tiempo sidéreo *aparente* es del orden de 1 segundo de tiempo,
    despreciable frente a otras aproximaciones de baja precisión ya
    asumidas en esta app (ver nota de ΔT en `app.solar.coordinates`).
    """
    t = julian_century(jd)
    theta0 = 280.46061837 + 360.98564736629 * (jd - J2000) + 0.000387933 * t**2 - t**3 / 38_710_000
    return theta0 % 360


def apparent_sidereal_time(jd: ArrayLike) -> float | np.ndarray:
    """Tiempo sidéreo aparente en Greenwich, en grados, normalizado a
    [0, 360): el medio más la ecuación de los equinoccios (Meeus cap. 12).
    Es el que corresponde al ángulo horario del Sol respecto al equinoccio
    verdadero de la fecha, que es en lo que están dadas α y δ aparentes.

    `jd` es un Día Juliano en UT; puede ser un float o un array de numpy.
    """
    return (mean_sidereal_time(jd) + equation_of_equinoxes(julian_century_tt(jd))) % 360


# ΔT = TT - UT, en segundos, a mitad de año (1 de julio) de 1990 a 2026:
# diferencia TT - UT1 calculada con las tablas IERS (vía astropy). Son datos
# medidos, así que superan a cualquier polinomio para la época reciente.
_DELTA_T_TABLE_FIRST_YEAR = 1990
_DELTA_T_TABLE = np.array(
    [
        57.22, 57.96, 58.74, 59.58, 60.40, 61.25, 62.00, 62.66, 63.28, 63.66,
        63.98, 64.21, 64.41, 64.55, 64.65, 64.80, 64.99, 65.34, 65.63, 65.95,
        66.24, 66.47, 66.77, 67.13, 67.49, 67.86, 68.40, 68.82, 69.11, 69.36,
        69.42, 69.35, 69.25, 69.22, 69.19, 69.14, 69.17,
    ]
)  # fmt: skip
_DELTA_T_TABLE_LAST_YEAR = _DELTA_T_TABLE_FIRST_YEAR + len(_DELTA_T_TABLE) - 1


def _delta_t_polynomial(year: float) -> float:
    """Aproximación polinómica de ΔT (Espenak y Meeus, NASA, 2006), en
    segundos, para el año decimal `year`. Cubre de -1999 a +3000."""
    if year < -500:
        u = (year - 1820) / 100
        return -20 + 32 * u**2
    if year < 500:
        u = year / 100
        return np.polyval(
            [0.0090316521, 0.022174192, -0.1798452, -5.952053, 33.78311, -1014.41, 10583.6], u
        )
    if year < 1600:
        u = (year - 1000) / 100
        return np.polyval(
            [0.0083572073, -0.005050998, -0.8503463, 0.319781, 71.23472, -556.01, 1574.2], u
        )
    if year < 1700:
        t = year - 1600
        return 120 - 0.9808 * t - 0.01532 * t**2 + t**3 / 7129
    if year < 1800:
        t = year - 1700
        return 8.83 + 0.1603 * t - 0.0059285 * t**2 + 0.00013336 * t**3 - t**4 / 1_174_000
    if year < 1860:
        t = year - 1800
        return np.polyval(
            [8.75e-10, -1.699e-7, 1.21272e-5, -3.7436e-4, 0.0041116, 0.0068612, -0.332447, 13.72],
            t,
        )
    if year < 1900:
        t = year - 1860
        return (
            7.62
            + 0.5737 * t
            - 0.251754 * t**2
            + 0.01680668 * t**3
            - 0.0004473624 * t**4
            + t**5 / 233_174
        )
    if year < 1920:
        t = year - 1900
        return -2.79 + 1.494119 * t - 0.0598939 * t**2 + 0.0061966 * t**3 - 0.000197 * t**4
    if year < 1941:
        t = year - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    if year < 1961:
        t = year - 1950
        return 29.07 + 0.407 * t - t**2 / 233 + t**3 / 2547
    if year < 1986:
        t = year - 1975
        return 45.45 + 1.067 * t - t**2 / 260 - t**3 / 718
    if year < 2005:
        t = year - 2000
        return np.polyval(
            [0.00002373599, 0.000651814, 0.0017275, -0.060374, 0.3345, 63.86],
            t,
        )
    if year < 2050:
        t = year - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    if year <= 2150:
        return -20 + 32 * ((year - 1820) / 100) ** 2 - 0.5628 * (2150 - year)
    return -20 + 32 * ((year - 1820) / 100) ** 2


def delta_t(jd: float) -> float:
    """ΔT = TT - UT, en segundos, para el instante `jd` (JD en UT).

    De 1990 a mediados de 2026 interpola datos medidos (IERS); antes usa los
    polinomios de Espenak y Meeus; después extrapola con el polinomio de
    2005-2050 corrido para empalmar con el último dato medido. Más allá de
    unas décadas del presente es un pronóstico (la rotación terrestre no es
    predecible): el error crece, pero sigue siendo mucho menor que la
    precisión del resto del motor para horarios solares.
    """
    year = 2000.0 + (jd - J2000) / 365.2425
    first = _DELTA_T_TABLE_FIRST_YEAR + 0.5
    last = _DELTA_T_TABLE_LAST_YEAR + 0.5
    if first <= year <= last:
        return float(np.interp(year, np.arange(first, last + 1), _DELTA_T_TABLE))
    if year > last:
        return _delta_t_polynomial(year) + (float(_DELTA_T_TABLE[-1]) - _delta_t_polynomial(last))
    return _delta_t_polynomial(year)


def julian_century_tt(jd_ut: ArrayLike) -> float | np.ndarray:
    """Siglos julianos desde J2000.0 en TT, para un JD dado en UT: el `t`
    que esperan las funciones de posición de `app.solar.coordinates`.

    `jd_ut` puede ser un float o un array de numpy (ΔT varía tan
    lentamente que se evalúa una sola vez, en el primer elemento).
    """
    jd = np.asarray(jd_ut, dtype=float)
    shift = delta_t(float(jd.flat[0])) / 86_400
    result = julian_century(jd + shift)
    return float(result) if result.ndim == 0 else result
