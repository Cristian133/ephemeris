import numpy as np
import pytest

from app.meteo.aggregate import distribution
from app.meteo.rain import RAINY_DAY_MM, rain_statistics
from app.meteo.series import DailySeries


def _series(precipitation: np.ndarray, start: str) -> DailySeries:
    dates = np.arange(
        np.datetime64(start),
        np.datetime64(start) + np.timedelta64(len(precipitation), "D"),
        dtype="datetime64[D]",
    )
    nan = np.full(len(dates), np.nan)
    return DailySeries(dates, precipitation, nan, nan, nan)


def _years(first: int, last: int, daily_mm_by_year) -> DailySeries:
    """Serie de varios años con un mm/día constante por año."""
    parts = []
    for year in range(first, last + 1):
        days = 366 if year % 4 == 0 else 365
        parts.append(np.full(days, daily_mm_by_year(year)))
    return _series(np.concatenate(parts), f"{first}-01-01")


def test_distribution_of_known_values() -> None:
    d = distribution(np.array([10.0, 20.0, 30.0, 40.0, 50.0, np.nan]))
    assert d.count == 5
    assert d.mean == pytest.approx(30.0)
    assert d.median == pytest.approx(30.0)
    assert d.p10 == pytest.approx(14.0)
    assert d.p90 == pytest.approx(46.0)


def test_distribution_without_data_is_all_none() -> None:
    d = distribution(np.array([np.nan, np.nan]))
    assert (d.count, d.mean, d.median, d.p10, d.p90) == (0, None, None, None, None)


def test_monthly_and_annual_totals_over_several_years() -> None:
    # 1 mm/día en 2019, 2 mm/día en 2020 y 3 mm/día en 2021.
    stats = rain_statistics(_years(2019, 2021, lambda y: y - 2018))
    assert stats.years == [2019, 2020, 2021]
    # Enero tiene 31 días: totales de 31, 62 y 93 mm.
    january = stats.monthly[0]
    assert january.count == 3
    assert january.mean == pytest.approx(62.0)
    assert january.median == pytest.approx(62.0)
    # Febrero: 28 (2019), 58 (2020 bisiesto), 84 (2021).
    assert stats.monthly[1].mean == pytest.approx((28 + 58 + 84) / 3)
    assert stats.yearly_totals == [pytest.approx(365), pytest.approx(732), pytest.approx(1095)]
    assert stats.annual.mean == pytest.approx((365 + 732 + 1095) / 3)


def test_wettest_and_driest_year() -> None:
    stats = rain_statistics(_years(2019, 2021, lambda y: {2019: 2.0, 2020: 0.5, 2021: 1.0}[y]))
    assert stats.wettest_year is not None and stats.wettest_year.year == 2019
    assert stats.driest_year is not None and stats.driest_year.year == 2020
    assert stats.wettest_year.total_mm == pytest.approx(730.0)


def test_rainy_days_use_the_one_millimetre_threshold() -> None:
    assert RAINY_DAY_MM == 1.0
    january = np.zeros(31)
    january[:5] = 1.0  # justo en el umbral: cuenta
    january[5:9] = 0.99  # apenas debajo: no cuenta
    stats = rain_statistics(_series(january, "2020-01-01"))
    assert stats.rainy_days[0] == pytest.approx(5.0)
    assert stats.rainy_days[1] is None  # sin datos de febrero


def test_incomplete_year_is_left_out_of_the_annual_figures() -> None:
    complete = _years(2019, 2019, lambda y: 1.0)
    partial = _series(np.full(31 + 28, 5.0), "2020-01-01")  # 2020: solo enero y febrero
    merged = DailySeries(
        np.concatenate([complete.dates, partial.dates]),
        np.concatenate([complete.precipitation_mm, partial.precipitation_mm]),
        np.full(len(complete) + len(partial), np.nan),
        np.full(len(complete) + len(partial), np.nan),
        np.full(len(complete) + len(partial), np.nan),
    )
    stats = rain_statistics(merged)
    assert stats.yearly_totals == [pytest.approx(365.0), None]
    assert stats.annual.count == 1
    # Pero los meses completos de 2020 sí cuentan en la climatología mensual.
    assert stats.monthly[0].count == 2
    assert stats.monthly[2].count == 1


def test_empty_series_gives_empty_statistics() -> None:
    stats = rain_statistics(_series(np.array([]), "2020-01-01"))
    assert stats.years == []
    assert stats.annual.count == 0
    assert stats.wettest_year is None and stats.driest_year is None
