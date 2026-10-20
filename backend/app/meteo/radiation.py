"""Radiación solar real frente a la de cielo despejado.

La radiación real es la de onda corta global horizontal del reanálisis
(MJ/m² por día, aquí en kWh/m²). Dividida por la que llegaría con cielo
despejado (modelo de Ineichen y Perez, `app.solar`) da el índice de
claridad: 1 es un cielo limpio, y cae con la nubosidad y la turbidez.
"""

from dataclasses import dataclass

import numpy as np

from app.meteo.aggregate import Distribution, distribution, monthly_table
from app.meteo.series import DailySeries
from app.meteo.sky import DAYS_IN_MONTH

_MJ_PER_KWH = 3.6


@dataclass(frozen=True)
class RadiationMonth:
    real: Distribution  # kWh/m² por día, entre los años
    clear_sky_kwh_per_day: float
    clearness_index: float | None  # media real / cielo despejado


@dataclass(frozen=True)
class RadiationStatistics:
    monthly: list[RadiationMonth]
    annual_real: Distribution  # kWh/m² del año, entre los años completos
    clear_sky_annual_kwh: float
    annual_clearness_index: float | None


def monthly_clear_sky_means(daily_kwh: np.ndarray) -> np.ndarray:
    """Media diaria (kWh/m²) de cada mes, a partir de 365 días de un año no bisiesto."""
    bounds = np.cumsum((0, *DAYS_IN_MONTH))
    return np.array([daily_kwh[bounds[m] : bounds[m + 1]].mean() for m in range(12)])


def radiation_statistics(
    series: DailySeries, clear_sky_daily_kwh: np.ndarray
) -> RadiationStatistics:
    """`clear_sky_daily_kwh`: energía de cielo despejado de cada día de un año no bisiesto."""
    clear_per_day = monthly_clear_sky_means(clear_sky_daily_kwh)
    kwh = series.radiation_mj_m2 / _MJ_PER_KWH
    _, per_day = monthly_table(series.dates, kwh, "mean")
    _, per_month_total = monthly_table(series.dates, kwh, "sum")
    yearly = np.where(np.isnan(per_month_total).any(axis=1), np.nan, per_month_total.sum(axis=1))

    monthly = []
    for m in range(12):
        dist = distribution(per_day[:, m])
        clear = float(clear_per_day[m])
        clearness = dist.mean / clear if dist.mean is not None and clear > 0 else None
        monthly.append(RadiationMonth(dist, clear, clearness))

    clear_annual = float(clear_sky_daily_kwh.sum())
    annual = distribution(yearly)
    return RadiationStatistics(
        monthly=monthly,
        annual_real=annual,
        clear_sky_annual_kwh=clear_annual,
        annual_clearness_index=(
            annual.mean / clear_annual if annual.mean is not None and clear_annual > 0 else None
        ),
    )


def estimate_panel_real_sky(
    panel_clear_monthly_kwh: list[float], stats: RadiationStatistics
) -> float | None:
    """Energía anual estimada (kWh por m² de panel) con el cielo real.

    Aproximación: a la energía de cielo despejado del panel de cada mes se le
    aplica el índice de claridad de ese mes, medido sobre el plano horizontal.
    Supone que las nubes restan lo mismo al panel inclinado que al horizontal;
    no separa directa y difusa, así que es una estimación, no un cálculo
    fotovoltaico. Un mes sin dato usa el índice anual; sin ninguno, `None`.
    """
    fallback = stats.annual_clearness_index
    total = 0.0
    for clear_kwh, month in zip(panel_clear_monthly_kwh, stats.monthly, strict=True):
        index = month.clearness_index if month.clearness_index is not None else fallback
        if index is None:
            return None
        total += clear_kwh * index
    return total
