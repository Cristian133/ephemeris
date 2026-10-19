"""Equinoccios y solsticios (Meeus cap. 27).

Algoritmo del libro (Tabla 27.A + términos periódicos de la Tabla 27.C),
válido para los años 1000 a 3000. Devuelve el instante en UT de los cuatro
eventos astronómicos del año — las estaciones son un asunto de hemisferio
(el equinoccio de marzo es el otoño austral y la primavera boreal), así que
el nombre de la estación lo pone quien presenta el dato, no este módulo.

Como en el resto del motor se ignora ΔT (TD-UT, ~1 minuto hoy): el JDE que
da el libro está en Tiempo Dinámico y acá se lo trata como UT. Es del orden
de la precisión de minutos del algoritmo, y consistente con
`app.solar.coordinates`.
"""

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.solar.time import datetime_from_julian_day

MIN_YEAR = 1000
MAX_YEAR = 3000

# Coeficientes del JDE medio (Tabla 27.A, años 1000-3000): polinomio en
# Y = (año - 2000) / 1000, de grado 4.
_MEAN_COEFFICIENTS = {
    "march_equinox": (2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057),
    "june_solstice": (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030),
    "september_equinox": (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078),
    "december_solstice": (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032),
}

# Términos periódicos (Tabla 27.C): (A, B en grados, C en grados/siglo).
_PERIODIC_TERMS = np.array(
    [
        (485, 324.96, 1934.136),
        (203, 337.23, 32964.467),
        (199, 342.08, 20.186),
        (182, 27.85, 445267.112),
        (156, 73.14, 45036.886),
        (136, 171.52, 22518.443),
        (77, 222.54, 65928.934),
        (74, 296.72, 3034.906),
        (70, 243.58, 9037.513),
        (58, 119.81, 33718.147),
        (52, 297.17, 150.678),
        (50, 21.02, 2281.226),
        (45, 247.54, 29929.562),
        (44, 325.15, 31555.956),
        (29, 60.93, 4443.417),
        (18, 155.12, 67555.328),
        (17, 288.79, 4562.452),
        (16, 198.04, 62894.029),
        (14, 199.76, 31436.921),
        (12, 95.39, 14577.848),
        (12, 287.11, 31931.756),
        (12, 320.81, 34777.259),
        (9, 227.73, 1222.114),
        (8, 15.45, 16859.074),
    ]
)


@dataclass(frozen=True)
class Seasons:
    """Los cuatro eventos astronómicos de un año calendario, en UT."""

    march_equinox: datetime
    june_solstice: datetime
    september_equinox: datetime
    december_solstice: datetime


def _event_jd(year: int, event: str) -> float:
    y = (year - 2000) / 1000
    a, b, c, d, e = _MEAN_COEFFICIENTS[event]
    jde0 = a + y * (b + y * (c + y * (d + y * e)))

    t = (jde0 - 2451545.0) / 36525.0
    w = np.radians(35999.373 * t - 2.47)
    delta_lambda = 1 + 0.0334 * np.cos(w) + 0.0007 * np.cos(2 * w)

    amplitude, phase, rate = _PERIODIC_TERMS.T
    s = float(np.sum(amplitude * np.cos(np.radians(phase + rate * t))))
    return jde0 + 0.00001 * s / float(delta_lambda)


def seasons(year: int) -> Seasons:
    """Equinoccios y solsticios del año gregoriano `year` (1000-3000)."""
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"year debe estar entre {MIN_YEAR} y {MAX_YEAR}")
    return Seasons(
        **{event: datetime_from_julian_day(_event_jd(year, event)) for event in _MEAN_COEFFICIENTS}
    )
