"""Perigeo y apogeo de la Luna (Meeus cap. 50): los instantes de mínima y
máxima distancia a la Tierra, y la distancia en cada uno.

Se calcula el instante medio (período anomalístico de 27.55 días) y se le
suman las correcciones periódicas de la tabla 50.A; la paralaje
horizontal de la tabla 50.B da la distancia con `sin π = 6378.14 / Δ`. El
resultado está en TT y se convierte a UT con ΔT.

Precisión declarada por el libro (1977-2022): el instante del perigeo
puede errar hasta ~31 minutos (la distancia casi no cambia cerca del
mínimo, y la perturbación del Sol desplaza el extremo) y el del apogeo
hasta ~3 minutos; la distancia, ~12 km en el perigeo y ~6 km en el apogeo.

Numeración: `k` entero es un perigeo y `k + 0.5` el apogeo siguiente;
`k = 0` es el perigeo del 22 de diciembre de 1999.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import cos, floor, radians, sin

from app.solar.apsides_terms import (
    APOGEO_PARALAJE,
    APOGEO_PARALAJE_BASE,
    APOGEO_TIEMPO,
    ARG_D,
    ARG_F,
    ARG_M,
    JDE_MEDIO,
    K_ANIO_BASE,
    K_DIVISOR_T,
    K_POR_ANIO,
    PERIGEO_PARALAJE,
    PERIGEO_PARALAJE_BASE,
    PERIGEO_TIEMPO,
    RADIO_ECUATORIAL_KM,
)
from app.solar.time import datetime_from_julian_day, delta_t, julian_day


class ApsisKind(StrEnum):
    PERIGEE = "perigee"
    APOGEE = "apogee"


@dataclass(frozen=True)
class Apsis:
    """Perigeo o apogeo de la Luna: instante (UT), distancia al centro de la
    Tierra y paralaje horizontal ecuatorial en segundos de arco."""

    kind: ApsisKind
    time: datetime
    distance_km: float
    parallax_arcsec: float
    k: float


def _polynomial(c: dict[str, float], k: float, t: float) -> float:
    return c["c0"] + c["k"] * k + t**2 * (c["t2"] + t * (c["t3"] + t * c["t4"]))


def apsis(k: float) -> Apsis:
    """Perigeo (`k` entero) o apogeo (`k` entero + 0.5) de número `k`."""
    if abs((k * 2) - round(k * 2)) > 1e-9:
        raise ValueError("k debe ser entero (perigeo) o entero más 0.5 (apogeo)")
    perigee = abs(k - round(k)) < 1e-9
    t = k / K_DIVISOR_T

    arguments = (
        radians(_polynomial({**ARG_D, "t4": ARG_D["t4"]}, k, t) % 360),
        radians(_polynomial(ARG_M, k, t) % 360),
        radians(_polynomial(ARG_F, k, t) % 360),
    )

    def argument(d: int, m: int, f: int) -> float:
        return d * arguments[0] + m * arguments[1] + f * arguments[2]

    time_terms = PERIGEO_TIEMPO if perigee else APOGEO_TIEMPO
    parallax_terms = PERIGEO_PARALAJE if perigee else APOGEO_PARALAJE
    base = PERIGEO_PARALAJE_BASE if perigee else APOGEO_PARALAJE_BASE

    jde = _polynomial(JDE_MEDIO, k, t) + sum(
        (coef + coef_t * t) * sin(argument(d, m, f)) for d, m, f, coef, coef_t in time_terms
    )
    parallax = base + sum(
        (coef + coef_t * t) * cos(argument(d, m, f)) for d, m, f, coef, coef_t in parallax_terms
    )
    distance = RADIO_ECUATORIAL_KM / sin(radians(parallax / 3600))
    return Apsis(
        kind=ApsisKind.PERIGEE if perigee else ApsisKind.APOGEE,
        time=datetime_from_julian_day(jde - delta_t(jde) / 86_400),
        distance_km=distance,
        parallax_arcsec=parallax,
        k=k,
    )


def apsides_between(start: datetime, end: datetime) -> list[Apsis]:
    """Perigeos y apogeos con `start <= instante < end` (UT), en orden
    cronológico. Las fechas naive se toman como UT."""
    start_naive, end_naive = start.replace(tzinfo=None), end.replace(tzinfo=None)
    decimal_year = 2000.0 + (julian_day(start) - 2451545.0) / 365.2425
    half = floor((decimal_year - K_ANIO_BASE) * K_POR_ANIO * 2) - 3
    result: list[Apsis] = []
    while True:
        event = apsis(half / 2)
        moment = event.time.replace(tzinfo=None)
        if moment >= end_naive:
            break
        if moment >= start_naive:
            result.append(event)
        half += 1
    return result


def apsides_in_year(year: int) -> list[Apsis]:
    """Perigeos y apogeos del año calendario `year` (en UT)."""
    return apsides_between(datetime(year, 1, 1), datetime(year + 1, 1, 1))
