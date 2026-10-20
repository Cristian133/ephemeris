"""Orientación óptima de un panel solar fijo.

Para cada inclinación candidata se integra, a lo largo del año, la
irradiancia que recibe el plano (modelo de cielo despejado de
`app.solar.irradiance`) y se elige la que más energía acumula. El azimut es
siempre hacia el ecuador: norte en el hemisferio sur, sur en el norte.

La irradiancia sobre el plano inclinado suma tres componentes:
- directa: DNI por el coseno del ángulo de incidencia;
- difusa: DHI con el modelo isótropo de Liu y Jordan, (1 + cos β) / 2
  (la bóveda celeste que "ve" el panel);
- reflejada por el suelo: GHI · albedo · (1 - cos β) / 2.

La difusa favorece inclinaciones algo menores que la directa sola, y la
reflejada (ej. nieve) algo mayores. Mismo alcance que `irradiance.py`:
cielo despejado, sin nubes ni sombras del entorno ni pérdidas del sistema
(temperatura, inversor), así que sirve como referencia de orientación, no
como dimensionamiento fotovoltaico.

Vectorizado con numpy: se muestrea un día de cada `_DAY_STEP` del año a
`_SAMPLES_PER_DAY` instantes y se evalúan todas las inclinaciones de una
vez, sin iterar en Python.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from app.solar.coordinates import declination, radius_vector, right_ascension
from app.solar.events import local_day_start_jd
from app.solar.horizontal import altitude, azimuth, hour_angle, local_sidereal_time
from app.solar.irradiance import DEFAULT_LINKE_TURBIDITY, clear_sky_components
from app.solar.time import apparent_sidereal_time, julian_century_tt

DEFAULT_ALBEDO = 0.2
"""Reflectividad del suelo por defecto (pasto/suelo típico); nieve fresca
ronda 0.8, asfalto 0.1."""

_DAY_STEP = 5
_SAMPLES_PER_DAY = 96
_TILTS = np.arange(0, 91, dtype=float)
_CURVE_STEP = 5


@dataclass(frozen=True)
class PanelOrientation:
    """Orientación óptima de un panel fijo para una ubicación y año.

    `azimuth_deg` es el rumbo hacia el que mira el panel (0°=Norte,
    180°=Sur). Las energías son kWh por m² de panel al año, con el panel
    en la inclinación indicada; `curve` es la energía anual para cada
    inclinación de 0° a 90° cada 5°. `monthly_kwh_per_m2` es la energía de
    cada mes (enero a diciembre) con el panel en la inclinación anual óptima;
    se estima con los días muestreados, así que suma el total anual con un
    error de pocos por ciento.
    """

    azimuth_deg: float
    annual_tilt_deg: float
    winter_tilt_deg: float
    summer_tilt_deg: float
    annual_kwh_per_m2: float
    horizontal_kwh_per_m2: float
    curve: list[tuple[float, float]]
    monthly_kwh_per_m2: list[float]


def _plane_power(
    jd: np.ndarray,
    latitude_deg: float,
    longitude_deg: float,
    panel_azimuth: float,
    elevation_m: float,
    linke_turbidity: float,
    albedo: float,
):
    """Potencia (W/m² de panel) en cada instante `jd` para cada inclinación
    de `_TILTS`: array de forma (len(jd), len(_TILTS))."""
    t = julian_century_tt(jd)
    alpha = right_ascension(t)
    delta = declination(t)
    lst = local_sidereal_time(apparent_sidereal_time(jd), longitude_deg)
    h = hour_angle(lst, alpha)

    alt = altitude(latitude_deg, delta, h)
    az = azimuth(latitude_deg, delta, h)
    dni, dhi, ghi = clear_sky_components(alt, radius_vector(t), elevation_m, linke_turbidity)

    alt_rad = np.radians(alt)[:, None]
    tilt_rad = np.radians(_TILTS)[None, :]
    delta_az = np.radians(az - panel_azimuth)[:, None]
    cos_incidence = np.sin(alt_rad) * np.cos(tilt_rad) + np.cos(alt_rad) * np.sin(
        tilt_rad
    ) * np.cos(delta_az)
    direct = dni[:, None] * np.clip(cos_incidence, 0.0, None)
    diffuse = dhi[:, None] * (1 + np.cos(tilt_rad)) / 2
    reflected = ghi[:, None] * albedo * (1 - np.cos(tilt_rad)) / 2
    return direct + diffuse + reflected


def _day_jd(year: int, month: int, day: int, longitude_deg: float) -> np.ndarray:
    jd0 = local_day_start_jd(date(year, month, day), longitude_deg)
    return jd0 + np.arange(_SAMPLES_PER_DAY, dtype=float) / _SAMPLES_PER_DAY


def optimal_panel_orientation(
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float = 0.0,
    linke_turbidity: float = DEFAULT_LINKE_TURBIDITY,
    albedo: float = DEFAULT_ALBEDO,
) -> PanelOrientation:
    """Orientación y inclinaciones óptimas de un panel fijo (anual, y para
    el solsticio de invierno y de verano) en el año `year`."""
    panel_azimuth = 0.0 if latitude_deg < 0 else 180.0

    days_in_year = 366 if calendar.isleap(year) else 365
    sampled_days = np.arange(0, days_in_year, _DAY_STEP, dtype=float)
    jan1 = local_day_start_jd(date(year, 1, 1), longitude_deg)
    day_fractions = np.arange(_SAMPLES_PER_DAY, dtype=float) / _SAMPLES_PER_DAY
    jd = (jan1 + sampled_days[:, None] + day_fractions[None, :]).ravel()
    hours_per_sample = 24 / _SAMPLES_PER_DAY
    params = (elevation_m, linke_turbidity, albedo)
    power = _plane_power(jd, latitude_deg, longitude_deg, panel_azimuth, *params)
    annual_kwh = power.sum(axis=0) * hours_per_sample * (days_in_year / len(sampled_days)) / 1000

    june = _plane_power(
        _day_jd(year, 6, 21, longitude_deg), latitude_deg, longitude_deg, panel_azimuth, *params
    )
    december = _plane_power(
        _day_jd(year, 12, 21, longitude_deg), latitude_deg, longitude_deg, panel_azimuth, *params
    )
    june_tilt = float(_TILTS[june.sum(axis=0).argmax()])
    december_tilt = float(_TILTS[december.sum(axis=0).argmax()])
    if latitude_deg < 0:  # el invierno austral es el solsticio de junio
        winter_tilt, summer_tilt = june_tilt, december_tilt
    else:
        winter_tilt, summer_tilt = december_tilt, june_tilt

    best = int(annual_kwh.argmax())
    daily_kwh = power[:, best].reshape(len(sampled_days), _SAMPLES_PER_DAY).sum(axis=1)
    daily_kwh = daily_kwh * hours_per_sample / 1000
    sampled_months = np.array(
        [(date(year, 1, 1) + timedelta(days=int(d))).month for d in sampled_days]
    )
    month_lengths = [calendar.monthrange(year, m)[1] for m in range(1, 13)]
    monthly_kwh = [
        float(daily_kwh[sampled_months == m].mean() * month_lengths[m - 1]) for m in range(1, 13)
    ]
    return PanelOrientation(
        azimuth_deg=panel_azimuth,
        annual_tilt_deg=float(_TILTS[best]),
        winter_tilt_deg=winter_tilt,
        summer_tilt_deg=summer_tilt,
        annual_kwh_per_m2=float(annual_kwh[best]),
        horizontal_kwh_per_m2=float(annual_kwh[0]),
        curve=[(float(_TILTS[i]), float(annual_kwh[i])) for i in range(0, 91, _CURVE_STEP)],
        monthly_kwh_per_m2=monthly_kwh,
    )
