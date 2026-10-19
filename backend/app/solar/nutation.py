"""Nutación en longitud y en oblicuidad (Meeus cap. 22, versión corta).

Meeus da dos niveles: la serie completa (63 términos, 0.0003") y una
versión reducida para cuando basta una precisión de ~0.5" en Δψ y ~0.1" en
Δε. Acá se usa la reducida: 4 términos cada una, que es más que suficiente
frente al error de 0.01° (36") del método de baja precisión de
`app.solar.coordinates`.

`t` son siglos julianos desde J2000.0 (en TD/TT) y puede ser un float o un
array de numpy.
"""

import numpy as np
from numpy.typing import ArrayLike

from app.solar.coordinates import FloatOrArray, mean_obliquity

_ARCSEC_TO_DEG = 1 / 3600


def _arguments(t: ArrayLike) -> tuple[FloatOrArray, FloatOrArray, FloatOrArray]:
    """Longitud del nodo ascendente de la Luna (Ω), longitud media del Sol
    (L) y de la Luna (L'), en radianes."""
    omega = np.radians(125.04452 - 1934.136261 * t)
    sun = np.radians(280.4665 + 36000.7698 * t)
    moon = np.radians(218.3165 + 481267.8813 * t)
    return omega, sun, moon


def nutation_in_longitude(t: ArrayLike) -> FloatOrArray:
    """Nutación en longitud (Δψ), en grados."""
    omega, sun, moon = _arguments(t)
    arcsec = (
        -17.20 * np.sin(omega)
        - 1.32 * np.sin(2 * sun)
        - 0.23 * np.sin(2 * moon)
        + 0.21 * np.sin(2 * omega)
    )
    return arcsec * _ARCSEC_TO_DEG


def nutation_in_obliquity(t: ArrayLike) -> FloatOrArray:
    """Nutación en oblicuidad (Δε), en grados."""
    omega, sun, moon = _arguments(t)
    arcsec = (
        9.20 * np.cos(omega)
        + 0.57 * np.cos(2 * sun)
        + 0.10 * np.cos(2 * moon)
        - 0.09 * np.cos(2 * omega)
    )
    return arcsec * _ARCSEC_TO_DEG


def true_obliquity(t: ArrayLike) -> FloatOrArray:
    """Oblicuidad verdadera de la eclíptica (ε = ε0 + Δε), en grados."""
    return mean_obliquity(t) + nutation_in_obliquity(t)


def equation_of_equinoxes(t: ArrayLike) -> FloatOrArray:
    """Ecuación de los equinoccios (Δψ·cos ε), en grados: diferencia entre el
    tiempo sidéreo aparente y el medio (Meeus cap. 12)."""
    return nutation_in_longitude(t) * np.cos(np.radians(true_obliquity(t)))
