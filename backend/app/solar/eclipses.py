"""Eclipses de Sol y de Luna (Meeus cap. 54).

Cada Luna nueva (eclipse solar) o llena (eclipse lunar) cerca de un nodo
de la órbita lunar puede producir un eclipse. El método del libro da, para
una lunación `k`: el instante del máximo (error medio 0.4 min), la
distancia mínima del eje de la sombra al centro de la Tierra (gamma, en
radios ecuatoriales terrestres), el radio del cono de sombra (u), el tipo
y la magnitud, y para los eclipses de Luna las semiduraciones de cada fase.

Alcance: son las condiciones *globales* (el libro excluye expresamente las
circunstancias locales de los eclipses solares, que requieren elementos
besselianos). Cerca del límite de visibilidad el método no es fiable: para
|gamma| casi igual a 0.9972 (central o no) o a 1.5433 + u (eclipse parcial
mínimo), y para magnitudes lunares de umbra casi nulas, el tipo y hasta la
existencia del eclipse pueden diferir del cálculo exacto. Los instantes
están en UT (el libro da TD; se resta ΔT).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import cos, floor, radians, sin, sqrt

from app.solar.eclipse_terms import (
    A1_COEFICIENTES,
    E_COEFICIENTES,
    F1_COEF_SIN_OMEGA,
    F_LUNA,
    F_SIN_ECLIPSE_GRADOS,
    GAMMA_CENTRAL_MAX,
    GAMMA_FACTOR_W,
    JDE_MEDIA,
    K_POR_ANIO,
    LIMITE_SOL_BASE,
    M_LUNA,
    M_SOL,
    OMEGA_COEF,
    OMEGA_LUNA,
    PENUMBRA_SOL_BASE,
    Q_CONSTANTE,
    TERMINOS_MAXIMO_LUNA,
    TERMINOS_MAXIMO_SOL,
    TERMINOS_P,
    TERMINOS_Q,
    TERMINOS_U,
    U_ANULAR_MIN,
    U_CONSTANTE,
)
from app.solar.time import datetime_from_julian_day, delta_t, julian_day

_LUNAR_CONSTANTS = {
    "mag_pen": 1.5573,
    "mag_umb": 1.0128,
    "mag_den": 0.5450,
    "p_base": 1.0128,
    "t_base": 0.4678,
    "h_base": 1.5573,
    "n_const": 0.5458,
    "n_cos": 0.0400,
}
"""Constantes de eclipses de Luna con la "regla francesa" (la que usa
Meeus por defecto): umbra y penumbra con el efecto de la atmósfera
terrestre según la Connaissance des Temps."""


class SolarKind(StrEnum):
    """Tipo de eclipse solar."""

    PARTIAL = "partial"
    ANNULAR = "annular"
    TOTAL = "total"
    HYBRID = "hybrid"  # anular-total


class LunarKind(StrEnum):
    """Tipo de eclipse lunar."""

    PENUMBRAL = "penumbral"
    PARTIAL = "partial"
    TOTAL = "total"


@dataclass(frozen=True)
class SolarEclipse:
    """Eclipse solar global.

    `time` es el instante (UT) del máximo del eclipse para la Tierra;
    `gamma` y `u` están en radios ecuatoriales terrestres (gamma positivo:
    el eje de la sombra pasa al norte del centro de la Tierra). `central`
    dice si hay línea central. `magnitude` es la magnitud máxima solo para
    los eclipses parciales (para los centrales el capítulo no da la
    magnitud, que depende del cociente de diámetros).
    """

    time: datetime
    kind: SolarKind
    central: bool
    gamma: float
    u: float
    magnitude: float | None
    k: int


@dataclass(frozen=True)
class LunarEclipse:
    """Eclipse lunar. Los contactos (UT) son `None` si esa fase no ocurre:
    un eclipse penumbral no tiene contactos con la umbra, y uno parcial no
    tiene totalidad. `umbral_magnitude` es negativa en los penumbrales."""

    time: datetime
    kind: LunarKind
    gamma: float
    u: float
    penumbral_magnitude: float
    umbral_magnitude: float
    penumbra_start: datetime
    penumbra_end: datetime
    partial_start: datetime | None
    partial_end: datetime | None
    total_start: datetime | None
    total_end: datetime | None
    k: float


def _polynomial(coefficients: tuple[float, ...], k: float, t: float) -> float:
    """c0 + c1*k + c2*T^2 + c3*T^3 + c4*T^4 (el término lineal es en `k`)."""
    c0, c1, *higher = coefficients
    return c0 + c1 * k + sum(c * t ** (i + 2) for i, c in enumerate(higher))


@dataclass(frozen=True)
class _Elements:
    k: float
    jde_mean: float
    e: float
    m: float
    mp: float
    f: float
    f1: float
    omega: float
    a1: float


def _elements(k: float) -> _Elements:
    t = k / 1236.85
    omega = _polynomial(OMEGA_LUNA, k, t) % 360
    f = _polynomial(F_LUNA, k, t) % 360
    return _Elements(
        k=k,
        jde_mean=_polynomial(JDE_MEDIA, k, t),
        e=E_COEFICIENTES[0] + E_COEFICIENTES[1] * t + E_COEFICIENTES[2] * t**2,
        m=_polynomial(M_SOL, k, t) % 360,
        mp=_polynomial(M_LUNA, k, t) % 360,
        f=f,
        f1=(f - F1_COEF_SIN_OMEGA * sin(radians(omega))) % 360,
        omega=omega,
        a1=_polynomial(A1_COEFICIENTES, k, t) % 360,
    )


def _argument(multiples: tuple[int, int, int, int, int], el: _Elements) -> float:
    c_m, c_mp, c_f1, c_a1, c_omega = multiples
    return radians(c_m * el.m + c_mp * el.mp + c_f1 * el.f1 + c_a1 * el.a1 + c_omega * el.omega)


def _sum(terms, el: _Elements, function) -> float:
    return sum(c * el.e**power * function(_argument(arg, el)) for c, power, arg in terms)


def _distance_to_node_multiple(f_deg: float) -> float:
    """Distancia de F al múltiplo de 180° más cercano."""
    remainder = f_deg % 180
    return min(remainder, 180 - remainder)


@dataclass(frozen=True)
class _Geometry:
    jde_max: float
    gamma: float
    u: float


def _geometry(el: _Elements, solar: bool) -> _Geometry:
    terms = TERMINOS_MAXIMO_SOL if solar else TERMINOS_MAXIMO_LUNA
    p = _sum(TERMINOS_P, el, sin)
    q = Q_CONSTANTE + _sum(TERMINOS_Q, el, cos)
    u = U_CONSTANTE + _sum(TERMINOS_U, el, cos)
    w = abs(cos(radians(el.f1)))
    gamma = (p * cos(radians(el.f1)) + q * sin(radians(el.f1))) * (1 - GAMMA_FACTOR_W * w)
    return _Geometry(el.jde_mean + _sum(terms, el, sin), gamma, u)


def _to_ut(jde: float) -> datetime:
    return datetime_from_julian_day(jde - delta_t(jde) / 86_400)


def solar_eclipse(k: int) -> SolarEclipse | None:
    """Eclipse solar de la Luna nueva de número `k` (k = 0 es la del 6 de
    enero de 2000), o `None` si no hay eclipse visible desde la Tierra."""
    el = _elements(float(k))
    if _distance_to_node_multiple(el.f) > F_SIN_ECLIPSE_GRADOS:
        return None
    geometry = _geometry(el, solar=True)
    gamma, u = geometry.gamma, geometry.u
    if abs(gamma) > LIMITE_SOL_BASE + u:
        return None

    central = abs(gamma) < GAMMA_CENTRAL_MAX
    non_central_umbral = not central and abs(gamma) < GAMMA_CENTRAL_MAX + abs(u)
    magnitude: float | None = None
    if central or non_central_umbral:
        if u < 0:
            kind = SolarKind.TOTAL
        elif u > U_ANULAR_MIN:
            kind = SolarKind.ANNULAR
        else:
            omega = OMEGA_COEF * sqrt(max(0.0, 1 - gamma**2))
            kind = SolarKind.HYBRID if u < omega else SolarKind.ANNULAR
    else:
        kind = SolarKind.PARTIAL
        magnitude = (LIMITE_SOL_BASE + u - abs(gamma)) / (PENUMBRA_SOL_BASE + 2 * u)

    return SolarEclipse(_to_ut(geometry.jde_max), kind, central, gamma, u, magnitude, k)


def lunar_eclipse(k: float) -> LunarEclipse | None:
    """Eclipse lunar de la Luna llena de número `k` (k = entero + 0.5), o
    `None` si no hay eclipse (ni siquiera penumbral)."""
    if abs((k % 1) - 0.5) > 1e-9:
        raise ValueError("k debe ser un entero más 0.5 (Luna llena)")
    el = _elements(k)
    if _distance_to_node_multiple(el.f) > F_SIN_ECLIPSE_GRADOS:
        return None
    geometry = _geometry(el, solar=False)
    gamma, u = abs(geometry.gamma), geometry.u
    c = _LUNAR_CONSTANTS

    penumbral = (c["mag_pen"] + u - gamma) / c["mag_den"]
    umbral = (c["mag_umb"] - u - gamma) / c["mag_den"]
    if penumbral <= 0:
        return None
    kind = (
        LunarKind.PENUMBRAL if umbral <= 0 else LunarKind.PARTIAL if umbral < 1 else LunarKind.TOTAL
    )

    # Semiduraciones (minutos): (60 / n) * sqrt(radio^2 - gamma^2).
    n = c["n_const"] + c["n_cos"] * cos(radians(el.mp))

    def half_duration(radius: float) -> float | None:
        return 60 / n * sqrt(radius**2 - gamma**2) if gamma < radius else None

    maximum = geometry.jde_max
    penumbra = half_duration(c["h_base"] + u)
    partial = half_duration(c["p_base"] - u)
    total = half_duration(c["t_base"] - u)

    def at(half: float | None, sign: int) -> datetime | None:
        return None if half is None else _to_ut(maximum + sign * half / 1440)

    return LunarEclipse(
        time=_to_ut(maximum),
        kind=kind,
        gamma=geometry.gamma,
        u=u,
        penumbral_magnitude=penumbral,
        umbral_magnitude=umbral,
        penumbra_start=at(penumbra, -1),
        penumbra_end=at(penumbra, +1),
        partial_start=at(partial, -1),
        partial_end=at(partial, +1),
        total_start=at(total, -1),
        total_end=at(total, +1),
        k=k,
    )


def eclipses_in_year(year: int) -> tuple[list[SolarEclipse], list[LunarEclipse]]:
    """Eclipses de Sol y de Luna cuyo máximo cae en el año calendario
    `year` (UT), en orden cronológico. Válido mientras la serie de Meeus
    lo sea: unos siglos alrededor del presente (el error crece con |T|)."""
    first = floor((year - 2000) * K_POR_ANIO) - 2
    last = first + int(K_POR_ANIO) + 6
    start = julian_day(datetime(year, 1, 1))
    end = julian_day(datetime(year + 1, 1, 1))

    solar: list[SolarEclipse] = []
    lunar: list[LunarEclipse] = []
    for k in range(first, last + 1):
        eclipse = solar_eclipse(k)
        if eclipse is not None and start <= julian_day(eclipse.time) < end:
            solar.append(eclipse)
        moon_eclipse = lunar_eclipse(k + 0.5)
        if moon_eclipse is not None and start <= julian_day(moon_eclipse.time) < end:
            lunar.append(moon_eclipse)
    return sorted(solar, key=lambda e: e.time), sorted(lunar, key=lambda e: e.time)
