"""Transformación de coordenadas ecuatoriales a horizontales: ángulo
horario, altitud y azimut (Meeus cap. 13).

Base directa de la trayectoria solar y la altitud a mediodía (puntos 3 y 4
del plan técnico, sección 5).

Como en `coordinates.py`, se usa `numpy` en vez de `math` para que estas
funciones vectoricen automáticamente sobre arrays (float normal o array de
numpy, indistintamente).

Convenciones:
- Longitud positiva al este (a diferencia del propio Meeus, que la toma
  positiva al oeste) — es la convención moderna más intuitiva, coincide
  con la de coordenadas GPS.
- Azimut medido desde el Norte en sentido horario (0°=N, 90°=E, 180°=S,
  270°=O) — convención de rumbo/compass moderna; Meeus lo mide desde el
  Sur.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatOrArray = float | NDArray[np.floating]
"""Un escalar o un array de numpy — todas las funciones del módulo aceptan
cualquiera de los dos y devuelven el tipo correspondiente."""


def wrap180(angle_deg: ArrayLike) -> FloatOrArray:
    """Normaliza un ángulo a (-180, 180]."""
    return (angle_deg + 180) % 360 - 180


def local_sidereal_time(
    greenwich_sidereal_time_deg: ArrayLike, longitude_deg: ArrayLike
) -> FloatOrArray:
    """Tiempo sidéreo local, en grados, normalizado a [0, 360)."""
    return (greenwich_sidereal_time_deg + longitude_deg) % 360


def hour_angle(local_sidereal_time_deg: ArrayLike, right_ascension_deg: ArrayLike) -> FloatOrArray:
    """Ángulo horario (H), en grados, normalizado a (-180, 180].

    H = tiempo sidéreo local - ascensión recta: negativo antes del tránsito
    (mañana), positivo después (tarde)."""
    return wrap180(local_sidereal_time_deg - right_ascension_deg)


def altitude(
    latitude_deg: ArrayLike, declination_deg: ArrayLike, hour_angle_deg: ArrayLike
) -> FloatOrArray:
    """Altitud (h) del Sol sobre el horizonte, en grados."""
    phi = np.radians(latitude_deg)
    delta = np.radians(declination_deg)
    h = np.radians(hour_angle_deg)
    sin_altitude = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(h)
    return np.degrees(np.arcsin(sin_altitude))


def azimuth(
    latitude_deg: ArrayLike, declination_deg: ArrayLike, hour_angle_deg: ArrayLike
) -> FloatOrArray:
    """Azimut (A) del Sol, en grados [0, 360), medido desde el Norte en
    sentido horario.

    Matemáticamente indeterminado cuando el Sol está exactamente en el
    cenit del observador (altitud 90°, latitud = declinación y H=0); en ese
    punto límite esta función devuelve 180° por convención de `atan2`, sin
    significado físico especial.
    """
    phi = np.radians(latitude_deg)
    delta = np.radians(declination_deg)
    h = np.radians(hour_angle_deg)
    y = np.sin(h)
    x = np.cos(h) * np.sin(phi) - np.tan(delta) * np.cos(phi)
    return (np.degrees(np.arctan2(y, x)) + 180) % 360
