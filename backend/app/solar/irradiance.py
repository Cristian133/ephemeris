"""Irradiancia solar en cielo despejado (fuente de respaldo: Meeus no
cubre radiometría; ver docs/plan_tecnico.md, secciones 4.6 y 10).

Modelo: masa de aire relativa según Kasten y Young (1989) y el modelo de
cielo despejado de Ineichen y Perez (2002), basado en el factor de
turbidez de Linke (TL). Es el modelo de cielo despejado de uso más común en
ingeniería solar (el que traen, por ejemplo, pvlib y SoDa/HelioClim), y
devuelve las tres componentes:

- DNI: irradiancia directa normal al haz.
- GHI: irradiancia global sobre una superficie horizontal.
- DHI: irradiancia difusa sobre una superficie horizontal (GHI menos la
  directa proyectada).

Respecto al modelo simple anterior (solo haz directo, Meinel y Meinel),
este suma la componente difusa (que con cielo despejado es 10-15% del
total, y bastante más con aire turbio o sol bajo), la altitud sobre el
nivel del mar (menos masa de aire, atmósfera más transparente) y la
turbidez como parámetro. Sigue siendo un modelo de cielo despejado: no hay
nubes, y TL es un valor típico, no una medición del lugar. Sirve para una
estimación realista del potencial solar, no para el diseño de precisión
de sistemas fotovoltaicos.

Como en `coordinates.py`/`horizontal.py`, se usa `numpy` para que estas
funciones vectoricen automáticamente sobre arrays."""

import numpy as np
from numpy.typing import ArrayLike

from app.solar.coordinates import FloatOrArray

SOLAR_CONSTANT = 1361.0
"""Constante solar (W/m²): irradiancia extraterrestre media a 1 UA del Sol
(TSI promedio de la era de medición satelital)."""

DEFAULT_LINKE_TURBIDITY = 3.0
"""Factor de turbidez de Linke por defecto: atmósfera limpia a levemente
turbia, típica de zonas templadas rurales (ciudades e industria: 4-6;
alta montaña: 1.5-2.5)."""

_SEA_LEVEL_PRESSURE_PA = 101_325.0


def extraterrestrial_irradiance(radius_vector_au: ArrayLike) -> FloatOrArray:
    """Irradiancia extraterrestre (W/m²) a la distancia Tierra-Sol dada
    (`radius_vector_au`, en UA — ver `coordinates.radius_vector`)."""
    return SOLAR_CONSTANT / radius_vector_au**2


def air_mass(altitude_deg: ArrayLike) -> FloatOrArray:
    """Masa de aire relativa (adimensional, 1 en el cenit) para la altitud
    solar dada, según el modelo de Kasten y Young (1989).

    Válida para altitud en [0°, 90°]; para altitud negativa (sol bajo el
    horizonte) el término `(96.07995 - zenith_deg)` puede volverse
    negativo y la potencia fraccionaria da `nan` — quien llama debe
    filtrar esos casos (`clear_sky_components` ya lo hace)."""
    zenith_deg = 90.0 - altitude_deg
    return 1.0 / (np.cos(np.radians(zenith_deg)) + 0.50572 * (96.07995 - zenith_deg) ** (-1.6364))


def pressure_ratio(elevation_m: ArrayLike) -> FloatOrArray:
    """Presión atmosférica a `elevation_m` sobre el nivel del mar, relativa
    a la del nivel del mar (atmósfera estándar internacional)."""
    return (1.0 - 2.25577e-5 * elevation_m) ** 5.25588


def clear_sky_components(
    altitude_deg: ArrayLike,
    radius_vector_au: ArrayLike,
    elevation_m: float = 0.0,
    linke_turbidity: float = DEFAULT_LINKE_TURBIDITY,
) -> tuple[FloatOrArray, FloatOrArray, FloatOrArray]:
    """Irradiancia de cielo despejado (Ineichen y Perez, 2002) para la
    altitud solar y el radio vector Tierra-Sol dados, en W/m²:
    `(dni, dhi, ghi)`.

    - `dni`: directa normal al haz (sobre una superficie perpendicular).
    - `dhi`: difusa sobre una superficie horizontal.
    - `ghi`: global sobre una superficie horizontal (= dni·sin(altitud) +
      dhi).

    Las tres son 0 cuando el Sol está en o bajo el horizonte
    (`altitude_deg <= 0`; no `-0.0`: se fuerza explícitamente, y no da NaN
    aunque la altitud sea muy negativa). `elevation_m` es la altitud del
    lugar sobre el nivel del mar y `linke_turbidity` el factor de turbidez
    (1 = aire seco y limpio; típicamente 2-5).
    """
    altitude_deg = np.asarray(altitude_deg, dtype=float)
    above = altitude_deg > 0
    sin_alt = np.sin(np.radians(np.clip(altitude_deg, 0.0, None)))

    # Masa de aire absoluta: la relativa, corregida por la presión del lugar
    # (evita indefinición bajo el horizonte recortando la altitud a 0).
    am = air_mass(np.clip(altitude_deg, 0.0, None)) * pressure_ratio(elevation_m)

    fh1 = np.exp(-elevation_m / 8000.0)
    fh2 = np.exp(-elevation_m / 1250.0)
    cg1 = 5.09e-5 * elevation_m + 0.868
    cg2 = 3.92e-5 * elevation_m + 0.0387
    i0 = extraterrestrial_irradiance(radius_vector_au)
    tl = linke_turbidity

    ghi = cg1 * i0 * sin_alt * np.exp(-cg2 * am * (fh1 + fh2 * (tl - 1.0))) * np.exp(0.01 * am**1.8)
    b = 0.664 + 0.163 / fh1
    dni = i0 * b * np.exp(-0.09 * am * (tl - 1.0))
    # La global nunca puede ser menor que la directa proyectada (el modelo
    # ajusta cada componente por separado, y con sol muy bajo pueden cruzarse).
    ghi = np.maximum(ghi, dni * sin_alt)
    dhi = ghi - dni * sin_alt

    zero = np.zeros_like(ghi)
    return np.where(above, dni, zero), np.where(above, dhi, zero), np.where(above, ghi, zero)
