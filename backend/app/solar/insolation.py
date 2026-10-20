"""Energía diaria de cielo despejado sobre una superficie horizontal.

Es la versión de todo un año de `events.daily_irradiation`: en lugar de un
día por llamada, evalúa los 365 días a la vez (vectorizado con numpy) con la
misma cadena de cálculo que `panel.py`. Sirve de techo físico para comparar
con la radiación que realmente llega (ver `app.meteo.radiation`).
"""

import calendar
from datetime import date

import numpy as np

from app.solar.coordinates import declination, radius_vector, right_ascension
from app.solar.events import local_day_start_jd
from app.solar.horizontal import altitude, hour_angle, local_sidereal_time
from app.solar.irradiance import (
    DEFAULT_LINKE_TURBIDITY,
    clear_sky_components,
    extraterrestrial_irradiance,
)
from app.solar.time import apparent_sidereal_time, julian_century_tt

_SAMPLES_PER_DAY = 96


def _day_samples(
    year: int, latitude_deg: float, longitude_deg: float
) -> tuple[np.ndarray, np.ndarray, int]:
    """Altitud solar (°) y radio vector (UA) de cada muestra del año, aplanados
    (días × muestras por día), y la cantidad de días."""
    days_in_year = 366 if calendar.isleap(year) else 365
    jan1 = local_day_start_jd(date(year, 1, 1), longitude_deg)
    fractions = np.arange(_SAMPLES_PER_DAY, dtype=float) / _SAMPLES_PER_DAY
    jd = (jan1 + np.arange(days_in_year, dtype=float)[:, None] + fractions[None, :]).ravel()

    t = julian_century_tt(jd)
    lst = local_sidereal_time(apparent_sidereal_time(jd), longitude_deg)
    h = hour_angle(lst, right_ascension(t))
    return altitude(latitude_deg, declination(t), h), radius_vector(t), days_in_year


def _daily_kwh(power_w: np.ndarray, days_in_year: int) -> np.ndarray:
    hours_per_sample = 24 / _SAMPLES_PER_DAY
    return power_w.reshape(days_in_year, _SAMPLES_PER_DAY).sum(axis=1) * hours_per_sample / 1000


def clear_sky_daily_ghi_kwh(
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float = 0.0,
    linke_turbidity: float = DEFAULT_LINKE_TURBIDITY,
) -> np.ndarray:
    """Energía global horizontal de cielo despejado (kWh/m²) de cada día del
    año, en el día solar local del observador. Un elemento por día."""
    alt, radius, days_in_year = _day_samples(year, latitude_deg, longitude_deg)
    _, _, ghi = clear_sky_components(alt, radius, elevation_m, linke_turbidity)
    return _daily_kwh(ghi, days_in_year)


def extraterrestrial_daily_kwh(year: int, latitude_deg: float, longitude_deg: float) -> np.ndarray:
    """Energía (kWh/m²) que llega a una superficie horizontal en el tope de la
    atmósfera, de cada día del año: el techo absoluto, sin atmósfera. Un
    elemento por día."""
    alt, radius, days_in_year = _day_samples(year, latitude_deg, longitude_deg)
    sin_alt = np.sin(np.radians(np.clip(alt, 0.0, None)))
    return _daily_kwh(extraterrestrial_irradiance(radius) * sin_alt, days_in_year)
