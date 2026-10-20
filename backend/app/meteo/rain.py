"""Estadísticas de lluvia: mensuales y anuales, a partir de la serie diaria."""

from dataclasses import dataclass

import numpy as np

from app.meteo.aggregate import Distribution, distribution, monthly_table
from app.meteo.series import DailySeries

# Convención de la OMM: día de lluvia es el que acumula 1 mm o más.
RAINY_DAY_MM = 1.0


@dataclass(frozen=True)
class YearTotal:
    year: int
    total_mm: float


@dataclass(frozen=True)
class RainStatistics:
    years: list[int]
    monthly: list[Distribution]  # índice 0 = enero
    rainy_days: list[float | None]  # media de días de lluvia por mes
    yearly_totals: list[float | None]  # None si falta algún mes del año
    annual: Distribution
    wettest_year: YearTotal | None
    driest_year: YearTotal | None


def rain_statistics(series: DailySeries) -> RainStatistics:
    years, totals = monthly_table(series.dates, series.precipitation_mm, "sum")
    rainy = np.where(
        np.isnan(series.precipitation_mm),
        np.nan,
        (series.precipitation_mm >= RAINY_DAY_MM).astype(float),
    )
    _, rainy_per_month = monthly_table(series.dates, rainy, "sum")

    # Un año entra en las estadísticas anuales solo con sus 12 meses completos.
    yearly = np.where(np.isnan(totals).any(axis=1), np.nan, totals.sum(axis=1))
    complete = [(int(y), float(t)) for y, t in zip(years, yearly, strict=True) if not np.isnan(t)]

    return RainStatistics(
        years=[int(y) for y in years],
        monthly=[distribution(totals[:, m]) for m in range(12)],
        rainy_days=[
            None
            if np.isnan(rainy_per_month[:, m]).all()
            else float(np.nanmean(rainy_per_month[:, m]))
            for m in range(12)
        ],
        yearly_totals=[None if np.isnan(t) else float(t) for t in yearly],
        annual=distribution(yearly),
        wettest_year=YearTotal(*max(complete, key=lambda c: c[1])) if complete else None,
        driest_year=YearTotal(*min(complete, key=lambda c: c[1])) if complete else None,
    )
