"""Fases de la Luna (Meeus cap. 49): instantes de Luna nueva, cuarto
creciente, Luna llena y cuarto menguante.

El método calcula el instante medio de cada fase a partir del número de
lunación `k` y le suma las correcciones periódicas de la tabla del libro
(`app.solar.phase_terms`). El resultado está en Tiempo Dinámico (TT);
aquí se convierte a UT restando ΔT, que es lo que ve un reloj. Error medio
del método: ~4 s (máximo ~17 s) frente a ELP-2000/82 para 1980-2020.

Numeración: `k` entero es una Luna nueva (k = 0 es la del 6 de enero de
2000); `k + 0.25` es el cuarto creciente, `k + 0.5` la Luna llena y
`k + 0.75` el cuarto menguante. La lunación de Brown (la numeración
histórica, con la primera Luna nueva de 1923 como lunación 1) es `k + 953`.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from math import floor

import numpy as np

from app.solar.phase_terms import (
    ADDITIONAL_CORRECTIONS,
    ANIO_BASE_K,
    E_COEF,
    F_COEF,
    JDE_MEDIO,
    K_POR_ANIO,
    K_POR_SIGLO,
    M_COEF,
    MP_COEF,
    NEW_FULL_MOON_TERMS,
    OMEGA_COEF,
    QUARTER_TERMS,
    W_CONSTANTE,
    W_TERMS,
)
from app.solar.time import J2000, datetime_from_julian_day, delta_t, julian_day

BROWN_LUNATION_OFFSET = 953
"""`k = 0` (Luna nueva del 6 de enero de 2000) es la lunación de Brown 953."""

MEAN_SYNODIC_MONTH_DAYS = 29.530588861


class PhaseKind(IntEnum):
    """Fase principal de la Luna; el valor es la parte fraccionaria de `k`
    multiplicada por 4."""

    NEW = 0
    FIRST_QUARTER = 1
    FULL = 2
    LAST_QUARTER = 3


@dataclass(frozen=True)
class MoonPhase:
    """Instante (UT) de una fase principal de la Luna."""

    kind: PhaseKind
    time: datetime
    k: float

    @property
    def brown_lunation(self) -> int:
        """Número de lunación de Brown del mes sinódico al que pertenece
        (el que comienza en la Luna nueva anterior o igual)."""
        return floor(self.k) + BROWN_LUNATION_OFFSET


def _polynomial(coefficients: tuple[float, ...], k: float, t: float) -> float:
    """c0 + c1*k + c2*T^2 + c3*T^3 + c4*T^4 (el término lineal es en `k`)."""
    c0, c1, c2, c3, c4 = (*coefficients, 0.0, 0.0, 0.0, 0.0, 0.0)[:5]
    return c0 + c1 * k + t**2 * (c2 + t * (c3 + t * c4))


def _argument_degrees(argument: tuple[int, int, int, int], angles: tuple[float, ...]) -> float:
    return sum(multiple * angle for multiple, angle in zip(argument, angles, strict=True))


def phase_jde(k: float) -> float:
    """JDE (Tiempo Dinámico) de la fase de número `k` (ver el docstring del
    módulo para su numeración). Lanza `ValueError` si `k` no es múltiplo
    de 0.25: cualquier otro valor no corresponde a una fase principal."""
    quarters = k * 4
    if abs(quarters - round(quarters)) > 1e-9:
        raise ValueError("k debe ser un múltiplo de 0.25")
    k = round(quarters) / 4
    kind = PhaseKind(round(quarters) % 4)

    t = k / K_POR_SIGLO
    e = 1.0 + E_COEF[1] * t + E_COEF[2] * t**2
    m = np.radians(_polynomial(M_COEF, k, t) % 360)
    mp = np.radians(_polynomial(MP_COEF, k, t) % 360)
    f = np.radians(_polynomial(F_COEF, k, t) % 360)
    omega = np.radians(_polynomial(OMEGA_COEF, k, t) % 360)
    angles = (m, mp, f, omega)

    jde = _polynomial(JDE_MEDIO, k, t)

    if kind in (PhaseKind.NEW, PhaseKind.FULL):
        column = 1 if kind is PhaseKind.NEW else 2
        correction = sum(
            term[column] * e ** term[3] * np.sin(_argument_degrees(term[0], angles))
            for term in NEW_FULL_MOON_TERMS
        )
    else:
        correction = sum(
            coefficient * e**power * np.sin(_argument_degrees(argument, angles))
            for argument, coefficient, power in QUARTER_TERMS
        )
        w = W_CONSTANTE + sum(
            coefficient * e**power * np.cos(_argument_degrees(argument, angles))
            for coefficient, power, argument in W_TERMS
        )
        correction += w if kind is PhaseKind.FIRST_QUARTER else -w

    additional = 0.0
    for base, speed, t2_coefficient, coefficient in ADDITIONAL_CORRECTIONS:
        planetary_angle = np.radians(base + speed * k + t2_coefficient * t**2)
        additional += coefficient * np.sin(planetary_angle)

    return float(jde + correction + additional)


def phase_time(k: float) -> datetime:
    """Instante (UT) de la fase de número `k`."""
    jde = phase_jde(k)
    return datetime_from_julian_day(jde - delta_t(jde) / 86_400)


def _k_near(jd: float) -> float:
    """Número de cuarto de lunación (4k) aproximado para un JD, por debajo."""
    decimal_year = 2000.0 + (jd - J2000) / 365.2425
    return floor((decimal_year - ANIO_BASE_K) * K_POR_ANIO * 4)


def phases_between(start: datetime, end: datetime) -> list[MoonPhase]:
    """Fases principales de la Luna con `start <= instante < end` (UT), en
    orden cronológico. Las fechas naive se toman como UT."""
    quarter = _k_near(julian_day(start)) - 2
    result: list[MoonPhase] = []
    while True:
        k = quarter / 4
        moment = phase_time(k)
        if moment.replace(tzinfo=None) >= end.replace(tzinfo=None):
            break
        if moment.replace(tzinfo=None) >= start.replace(tzinfo=None):
            result.append(MoonPhase(PhaseKind(quarter % 4), moment, k))
        quarter += 1
    return result


def phases_in_year(year: int) -> list[MoonPhase]:
    """Fases principales de la Luna del año calendario `year` (en UT)."""
    return phases_between(datetime(year, 1, 1), datetime(year + 1, 1, 1))


def previous_new_moon(jd_ut: float) -> MoonPhase:
    """La Luna nueva más reciente anterior o igual al instante `jd_ut`."""
    quarter = (_k_near(jd_ut) // 4) * 4 + 4
    while True:
        k = quarter / 4
        moment = phase_time(k)
        if julian_day(moment) <= jd_ut:
            return MoonPhase(PhaseKind.NEW, moment, k)
        quarter -= 4


def moon_age_days(jd_ut: float) -> float:
    """Edad de la Luna: días transcurridos desde la última Luna nueva."""
    return jd_ut - julian_day(previous_new_moon(jd_ut).time)
