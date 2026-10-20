import numpy as np
import pytest

from app.meteo.radiation import (
    estimate_panel_real_sky,
    monthly_clear_sky_means,
    radiation_statistics,
)
from app.meteo.series import DailySeries


def _year(radiation_kwh: float | np.ndarray, start: str = "2021-01-01", days: int = 365):
    values = (
        np.full(days, radiation_kwh * 3.6) if np.isscalar(radiation_kwh) else radiation_kwh * 3.6
    )
    dates = np.arange(
        np.datetime64(start),
        np.datetime64(start) + np.timedelta64(days, "D"),
        dtype="datetime64[D]",
    )
    nan = np.full(days, np.nan)
    return DailySeries(dates, nan, nan, nan, values)


def test_monthly_clear_sky_means_average_each_month() -> None:
    daily = np.concatenate([np.full(31, 1.0), np.full(28, 2.0), np.full(306, 3.0)])
    means = monthly_clear_sky_means(daily)
    assert means[0] == pytest.approx(1.0) and means[1] == pytest.approx(2.0)
    assert means[2:] == pytest.approx(3.0)


def test_clearness_index_is_real_over_clear_sky() -> None:
    clear = np.full(365, 6.0)
    stats = radiation_statistics(_year(4.5), clear)
    assert stats.monthly[0].real.mean == pytest.approx(4.5)  # MJ convertidos a kWh
    assert stats.monthly[0].clearness_index == pytest.approx(0.75)
    assert stats.annual_real.mean == pytest.approx(4.5 * 365)
    assert stats.clear_sky_annual_kwh == pytest.approx(6.0 * 365)
    assert stats.annual_clearness_index == pytest.approx(0.75)


def test_clearness_index_is_none_without_clear_sky_energy() -> None:
    clear = np.full(365, 6.0)
    clear[:31] = 0.0  # noche polar en enero
    stats = radiation_statistics(_year(1.0), clear)
    assert stats.monthly[0].clearness_index is None
    assert stats.monthly[1].clearness_index == pytest.approx(1 / 6)


def test_annual_figures_need_a_complete_year() -> None:
    stats = radiation_statistics(_year(4.0, days=100), np.full(365, 6.0))
    assert stats.annual_real.count == 0
    assert stats.annual_clearness_index is None
    assert stats.monthly[0].clearness_index == pytest.approx(4 / 6)  # enero sí está completo


def test_panel_estimate_applies_each_months_clearness_index() -> None:
    clear = np.full(365, 6.0)
    values = np.concatenate([np.full(31, 3.0), np.full(334, 6.0)])  # enero a la mitad
    stats = radiation_statistics(_year(values), clear)
    panel_clear = [100.0] * 12
    assert estimate_panel_real_sky(panel_clear, stats) == pytest.approx(50 + 11 * 100)


def test_panel_estimate_falls_back_to_the_annual_index_or_gives_up() -> None:
    clear = np.full(365, 6.0)
    stats = radiation_statistics(_year(3.0, days=365), clear)
    # Un mes sin índice usa el anual (0.5).
    gap = radiation_statistics(_year(3.0), np.concatenate([np.zeros(31), np.full(334, 6.0)]))
    assert estimate_panel_real_sky([100.0] * 12, gap) == pytest.approx(
        100 * 0.5 * 11 + 100 * (gap.annual_clearness_index or 0)
    )
    no_data = radiation_statistics(_year(3.0, days=20), np.zeros(365))
    assert estimate_panel_real_sky([100.0] * 12, no_data) is None
    assert stats.annual_clearness_index == pytest.approx(0.5)
