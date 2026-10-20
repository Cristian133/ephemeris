"""Agregación de series diarias en tablas año × mes (numpy, sin red)."""

from dataclasses import dataclass
from typing import Literal

import numpy as np


def monthly_table(
    dates: np.ndarray, values: np.ndarray, how: Literal["sum", "mean"]
) -> tuple[np.ndarray, np.ndarray]:
    """Agrega `values` (un valor por día) a una tabla de forma (años, 12).

    Devuelve los años (ascendente) y la tabla; `NaN` donde el mes no se puede
    resumir con honestidad:

    - `sum` (ej. lluvia total del mes) exige el mes completo y sin huecos:
      una suma parcial subestimaría y arruinaría el promedio climático.
    - `mean` (ej. nubosidad media) tolera huecos, pero no un mes sin ningún dato.
    """
    days = dates.astype("datetime64[D]")
    if len(days) == 0:
        return np.array([], dtype=int), np.empty((0, 12))
    months = days.astype("datetime64[M]")
    years = np.arange(
        months.min().astype("datetime64[Y]").astype(int) + 1970,
        months.max().astype("datetime64[Y]").astype(int) + 1971,
    )
    table = np.full((len(years), 12), np.nan)
    for month in np.unique(months):
        in_month = months == month
        month_values = values[in_month]
        year_index = month.astype("datetime64[Y]").astype(int) + 1970 - years[0]
        month_number = int(month.astype(int) % 12)
        if how == "sum":
            next_month = month + np.timedelta64(1, "M")
            expected_days = int(
                (next_month.astype("datetime64[D]") - month.astype("datetime64[D]")).astype(int)
            )
            if len(month_values) == expected_days and not np.isnan(month_values).any():
                table[year_index, month_number] = month_values.sum()
        elif not np.isnan(month_values).all():
            table[year_index, month_number] = np.nanmean(month_values)
    return years, table


@dataclass(frozen=True)
class Distribution:
    """Resumen de una magnitud a lo largo de los años con dato.

    Todo es `None` si no hay ningún año utilizable; `count` dice con
    cuántos años se calculó (con pocos, los percentiles son poco fiables).
    """

    count: int
    mean: float | None
    median: float | None
    p10: float | None
    p90: float | None


def distribution(values: np.ndarray) -> Distribution:
    valid = values[~np.isnan(values)]
    if len(valid) == 0:
        return Distribution(0, None, None, None, None)
    p10, median, p90 = np.percentile(valid, [10, 50, 90])
    return Distribution(
        count=len(valid),
        mean=float(valid.mean()),
        median=float(median),
        p10=float(p10),
        p90=float(p90),
    )
