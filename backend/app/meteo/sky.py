"""Nubosidad y horas de sol reales, y su relación con el sol astronómico.

La insolación relativa compara las horas de sol efectivo (la fuente las da
del reanálisis, con radiación directa útil) con la duración astronómica del
día: cuánto del tiempo en que el Sol está sobre el horizonte llega a brillar.
La duración astronómica sale del motor solar (`app.solar.events`).
"""

from dataclasses import dataclass

import numpy as np

from app.meteo.aggregate import Distribution, distribution, monthly_table
from app.meteo.series import DailySeries
from app.solar.events import sunrise_sunset_year

# Un día es despejado con nubosidad media de hasta 20 %, y cubierto desde 80 %
# (equivale a ~2/8 y ~6/8 de cielo cubierto); el resto, parcialmente nublado.
CLEAR_MAX_PCT = 20.0
OVERCAST_MIN_PCT = 80.0

# La duración del día casi no cambia de un año a otro (menos de un minuto):
# alcanza con un año de referencia, no bisiesto, para la climatología.
REFERENCE_YEAR = 2021
DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


# Relación de Ångström-Prescott: la fracción de radiación extraterrestre que
# llega al suelo (índice de claridad kt) crece linealmente con la fracción de
# horas de sol, kt = a + b·n/N.
#
# Coeficientes ajustados con veinte estaciones del SMN, la AEMET, la JMA y el
# HKO (Argentina, España, Japón y Hong Kong; scripts/validar_estaciones.py,
# `--ajustar`). La relación depende del clima: un ajuste hecho solo con
# Argentina y Madrid subestimaba 11 % en Asia, y uno hecho solo con Asia
# sobreestimaba 16 % en Argentina y Madrid. Con las veinte juntas, en
# validación cruzada (cada estación fuera del ajuste) el error anual medio es
# de 9 % y el sesgo medio de +0.3 %, contra 11 % y +11 % con los de FAO-56. Su
# suma (0.78) es la clásica de Ångström. No están comprobados en trópico
# húmedo continental, desierto ni latitudes altas del norte.
ANGSTROM_A = 0.27
ANGSTROM_B = 0.51
# Los de FAO-56, que no se ajustan a ningún clima en particular; la referencia.
FAO_ANGSTROM_A = 0.25
FAO_ANGSTROM_B = 0.50


@dataclass(frozen=True)
class CloudMonth:
    cover: Distribution  # % medio del mes, entre los años
    clear_days: float | None  # medias de días por mes
    partly_days: float | None
    overcast_days: float | None


@dataclass(frozen=True)
class CloudStatistics:
    monthly: list[CloudMonth]
    annual: Distribution  # % medio anual, entre los años con los 12 meses


@dataclass(frozen=True)
class SunshineMonth:
    hours_per_day: Distribution  # horas de sol por día, entre los años
    astronomical_hours_per_day: float
    relative_pct: float | None  # media / astronómicas, None si no hay sol posible


@dataclass(frozen=True)
class SunshineStatistics:
    monthly: list[SunshineMonth]
    annual_hours: Distribution  # horas de sol del año, entre los años completos
    astronomical_annual_hours: float
    annual_relative_pct: float | None


def _mean_over_years(table: np.ndarray, month: int) -> float | None:
    column = table[:, month]
    return None if np.isnan(column).all() else float(np.nanmean(column))


def _indicator(values: np.ndarray, condition: np.ndarray) -> np.ndarray:
    return np.where(np.isnan(values), np.nan, condition.astype(float))


def cloud_statistics(series: DailySeries) -> CloudStatistics:
    cover = series.cloud_cover_pct
    _, mean_table = monthly_table(series.dates, cover, "mean")
    with np.errstate(invalid="ignore"):  # comparar con NaN avisa; el NaN se conserva
        clear = _indicator(cover, cover <= CLEAR_MAX_PCT)
        overcast = _indicator(cover, cover >= OVERCAST_MIN_PCT)
        partly = _indicator(cover, (cover > CLEAR_MAX_PCT) & (cover < OVERCAST_MIN_PCT))
    _, clear_table = monthly_table(series.dates, clear, "sum")
    _, partly_table = monthly_table(series.dates, partly, "sum")
    _, overcast_table = monthly_table(series.dates, overcast, "sum")

    yearly = np.where(np.isnan(mean_table).any(axis=1), np.nan, mean_table.mean(axis=1))
    return CloudStatistics(
        monthly=[
            CloudMonth(
                cover=distribution(mean_table[:, m]),
                clear_days=_mean_over_years(clear_table, m),
                partly_days=_mean_over_years(partly_table, m),
                overcast_days=_mean_over_years(overcast_table, m),
            )
            for m in range(12)
        ],
        annual=distribution(yearly),
    )


def astronomical_daylight_hours(latitude: float, longitude: float) -> np.ndarray:
    """Duración astronómica media del día (horas) de cada mes, forma (12,).

    Orto a ocaso del Sol con refracción. En un día polar sin salida ni puesta
    cuenta 24 h si el Sol no se pone y 0 h si no sale.
    """
    year = sunrise_sunset_year(REFERENCE_YEAR, latitude, longitude)
    hours = np.array(
        [
            (sunset - sunrise).total_seconds() / 3600
            if sunrise and sunset
            else (24.0 if above else 0.0)
            for sunrise, sunset, above in zip(
                year.sunrise, year.sunset, year.always_above, strict=True
            )
        ]
    )
    bounds = np.cumsum((0, *DAYS_IN_MONTH))
    return np.array([hours[bounds[m] : bounds[m + 1]].mean() for m in range(12)])


def sunshine_statistics(series: DailySeries, daylight_hours: np.ndarray) -> SunshineStatistics:
    """`daylight_hours`: duración astronómica media del día de cada mes (12)."""
    hours = series.sunshine_s / 3600
    _, per_day = monthly_table(series.dates, hours, "mean")
    _, per_month_total = monthly_table(series.dates, hours, "sum")
    yearly_total = np.where(
        np.isnan(per_month_total).any(axis=1), np.nan, per_month_total.sum(axis=1)
    )

    monthly = []
    for m in range(12):
        dist = distribution(per_day[:, m])
        astro = float(daylight_hours[m])
        relative = dist.mean / astro * 100 if dist.mean is not None and astro > 0 else None
        monthly.append(SunshineMonth(dist, astro, relative))

    astro_annual = float(np.dot(daylight_hours, DAYS_IN_MONTH))
    annual = distribution(yearly_total)
    annual_relative = (
        annual.mean / astro_annual * 100 if annual.mean is not None and astro_annual > 0 else None
    )
    return SunshineStatistics(
        monthly=monthly,
        annual_hours=annual,
        astronomical_annual_hours=astro_annual,
        annual_relative_pct=annual_relative,
    )


def estimated_sunshine_statistics(
    series: DailySeries,
    extraterrestrial_daily_kwh: np.ndarray,
    daylight_hours: np.ndarray,
    a: float = ANGSTROM_A,
    b: float = ANGSTROM_B,
) -> SunshineStatistics:
    """Horas de sol estimadas a partir de la radiación, con Ångström-Prescott.

    La duración de sol efectivo que modela el reanálisis queda 30-85 % por
    encima de lo medido con heliógrafo (más del doble en un clima subpolar),
    pero su radiación es mucho más fiel. Invertir la relación de
    Ångström-Prescott sobre la radiación da horas de sol mucho más cercanas
    a las medidas (ver docs/plan_tecnico.md, 7.3).

    Se aplica a cada mes de cada año: n/N = (kt - a) / b, con kt la radiación
    real sobre la extraterrestre, limitada a [0, 1]. `extraterrestrial_daily_kwh`
    son los 365 días de un año no bisiesto; `daylight_hours` la duración media
    del día de cada mes (12).
    """
    et_per_month = np.array(
        [
            extraterrestrial_daily_kwh[start : start + days].mean()
            for start, days in zip(np.cumsum((0, *DAYS_IN_MONTH[:-1])), DAYS_IN_MONTH, strict=True)
        ]
    )
    _, radiation = monthly_table(series.dates, series.radiation_mj_m2 / 3.6, "mean")
    kt = radiation / et_per_month
    fraction = np.clip((kt - a) / b, 0.0, 1.0)  # NaN se conserva
    per_day = fraction * daylight_hours

    monthly = []
    for m in range(12):
        dist = distribution(per_day[:, m])
        astro = float(daylight_hours[m])
        relative = dist.mean / astro * 100 if dist.mean is not None and astro > 0 else None
        monthly.append(SunshineMonth(dist, astro, relative))

    days = np.array(DAYS_IN_MONTH)
    yearly_total = np.where(np.isnan(per_day).any(axis=1), np.nan, (per_day * days).sum(axis=1))
    astro_annual = float(np.dot(daylight_hours, days))
    annual = distribution(yearly_total)
    annual_relative = (
        annual.mean / astro_annual * 100 if annual.mean is not None and astro_annual > 0 else None
    )
    return SunshineStatistics(
        monthly=monthly,
        annual_hours=annual,
        astronomical_annual_hours=astro_annual,
        annual_relative_pct=annual_relative,
    )
