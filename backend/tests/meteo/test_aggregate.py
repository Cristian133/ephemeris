import numpy as np
import pytest

from app.meteo.aggregate import monthly_table


def _days(start: str, end: str) -> np.ndarray:
    return np.arange(
        np.datetime64(start), np.datetime64(end) + np.timedelta64(1, "D"), dtype="datetime64[D]"
    )


def test_sum_of_a_complete_month() -> None:
    dates = _days("2021-02-01", "2021-02-28")
    years, table = monthly_table(dates, np.ones(len(dates)), "sum")
    assert list(years) == [2021]
    assert table[0, 1] == pytest.approx(28.0)
    assert np.isnan(table[0, [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]]).all()


def test_february_length_follows_leap_years() -> None:
    dates = _days("2020-02-01", "2020-02-29")
    _, table = monthly_table(dates, np.ones(len(dates)), "sum")
    assert table[0, 1] == pytest.approx(29.0)


def test_sum_is_nan_when_the_month_is_incomplete_or_has_gaps() -> None:
    partial = _days("2021-03-01", "2021-03-30")  # falta el 31
    assert np.isnan(monthly_table(partial, np.ones(len(partial)), "sum")[1][0, 2])
    full = _days("2021-03-01", "2021-03-31")
    values = np.ones(len(full))
    values[10] = np.nan
    assert np.isnan(monthly_table(full, values, "sum")[1][0, 2])


def test_mean_tolerates_gaps_but_not_an_empty_month() -> None:
    dates = _days("2021-03-01", "2021-04-30")
    values = np.where(dates < np.datetime64("2021-04-01"), 50.0, np.nan)
    values[0] = np.nan
    _, table = monthly_table(dates, values, "mean")
    assert table[0, 2] == pytest.approx(50.0)
    assert np.isnan(table[0, 3])


def test_multiple_years_fill_the_year_axis_including_gaps() -> None:
    dates = np.concatenate([_days("2019-01-01", "2019-01-31"), _days("2021-01-01", "2021-01-31")])
    years, table = monthly_table(dates, np.full(len(dates), 2.0), "sum")
    assert list(years) == [2019, 2020, 2021]
    assert table[0, 0] == pytest.approx(62.0)
    assert np.isnan(table[1]).all()
    assert table[2, 0] == pytest.approx(62.0)


def test_empty_input_gives_an_empty_table() -> None:
    years, table = monthly_table(np.array([], dtype="datetime64[D]"), np.array([]), "sum")
    assert len(years) == 0
    assert table.shape == (0, 12)
