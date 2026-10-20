import numpy as np
import pytest

from app.meteo.series import DailySeries
from app.meteo.sky import (
    ANGSTROM_A,
    ANGSTROM_B,
    FAO_ANGSTROM_A,
    FAO_ANGSTROM_B,
    astronomical_daylight_hours,
    cloud_statistics,
    estimated_sunshine_statistics,
    sunshine_statistics,
)

_DAYS_2021 = 365


def _series(start: str, **columns: np.ndarray) -> DailySeries:
    size = len(next(iter(columns.values())))
    dates = np.arange(
        np.datetime64(start),
        np.datetime64(start) + np.timedelta64(size, "D"),
        dtype="datetime64[D]",
    )
    nan = np.full(size, np.nan)
    return DailySeries(
        dates,
        columns.get("precipitation_mm", nan),
        columns.get("cloud_cover_pct", nan),
        columns.get("sunshine_s", nan),
        columns.get("radiation_mj_m2", nan),
    )


def test_cloud_days_are_classified_by_the_documented_thresholds() -> None:
    january = np.concatenate([np.full(10, 10.0), np.full(11, 50.0), np.full(10, 90.0)])
    stats = cloud_statistics(_series("2020-01-01", cloud_cover_pct=january))
    month = stats.monthly[0]
    assert (month.clear_days, month.partly_days, month.overcast_days) == (10, 11, 10)
    assert month.cover.mean == pytest.approx((10 * 10 + 11 * 50 + 10 * 90) / 31)


def test_cloud_thresholds_are_inclusive_at_the_clear_and_overcast_ends() -> None:
    january = np.concatenate([np.full(15, 20.0), np.full(16, 80.0)])
    month = cloud_statistics(_series("2020-01-01", cloud_cover_pct=january)).monthly[0]
    assert (month.clear_days, month.partly_days, month.overcast_days) == (15, 0, 16)


def test_cloud_classification_needs_a_complete_month() -> None:
    month = cloud_statistics(
        _series("2020-01-01", cloud_cover_pct=np.full(20, 10.0))  # el mes termina el día 20
    ).monthly[0]
    assert month.clear_days is None
    assert month.cover.mean == pytest.approx(10.0)  # la media tolera el mes parcial


def test_cloud_annual_needs_all_twelve_months() -> None:
    full = cloud_statistics(_series("2021-01-01", cloud_cover_pct=np.full(_DAYS_2021, 40.0)))
    assert full.annual.count == 1
    assert full.annual.mean == pytest.approx(40.0)
    partial = cloud_statistics(_series("2021-01-01", cloud_cover_pct=np.full(100, 40.0)))
    assert partial.annual.count == 0


def test_daylight_at_the_equator_is_about_twelve_hours_all_year() -> None:
    hours = astronomical_daylight_hours(0.0, 0.0)
    assert hours.shape == (12,)
    assert np.all((hours > 12.0) & (hours < 12.3))  # con refracción y semidiámetro


def test_daylight_follows_the_seasons_in_each_hemisphere() -> None:
    south = astronomical_daylight_hours(-34.5, -58.5)
    assert 14.0 < south[11] < 14.6 and 9.6 < south[5] < 10.3
    north = astronomical_daylight_hours(40.0, -3.7)
    assert north[5] > north[11]


def test_daylight_counts_polar_day_and_night() -> None:
    hours = astronomical_daylight_hours(80.0, 0.0)
    assert hours[11] == pytest.approx(0.0) and hours[5] == pytest.approx(24.0)


def test_sunshine_hours_and_relative_insolation() -> None:
    eight_hours = np.full(_DAYS_2021, 8 * 3600.0)
    stats = sunshine_statistics(_series("2021-01-01", sunshine_s=eight_hours), np.full(12, 12.0))
    assert stats.monthly[0].hours_per_day.mean == pytest.approx(8.0)
    assert stats.monthly[0].relative_pct == pytest.approx(8 / 12 * 100)
    assert stats.annual_hours.mean == pytest.approx(8 * _DAYS_2021)
    assert stats.astronomical_annual_hours == pytest.approx(12 * _DAYS_2021)
    assert stats.annual_relative_pct == pytest.approx(8 / 12 * 100)


def test_relative_insolation_is_none_without_possible_sunshine() -> None:
    daylight = np.full(12, 12.0)
    daylight[0] = 0.0  # noche polar en enero
    stats = sunshine_statistics(_series("2021-01-01", sunshine_s=np.zeros(_DAYS_2021)), daylight)
    assert stats.monthly[0].relative_pct is None
    assert stats.monthly[1].relative_pct == pytest.approx(0.0)


def test_sunshine_annual_total_skips_incomplete_years() -> None:
    stats = sunshine_statistics(
        _series("2021-01-01", sunshine_s=np.full(100, 3600.0)), np.full(12, 12.0)
    )
    assert stats.annual_hours.count == 0
    assert stats.annual_relative_pct is None


def _radiation_series(kt: float, extraterrestrial: np.ndarray) -> DailySeries:
    """Radiación diaria igual a `kt` por la extraterrestre, en MJ/m²."""
    return _series("2021-01-01", radiation_mj_m2=extraterrestrial * kt * 3.6)


def test_angstrom_prescott_inverts_the_clearness_index() -> None:
    et = np.full(_DAYS_2021, 10.0)
    daylight = np.full(12, 12.0)
    # Con kt = a + b/2 la mitad del día brilla, para los coeficientes que sean.
    for a, b in ((ANGSTROM_A, ANGSTROM_B), (FAO_ANGSTROM_A, FAO_ANGSTROM_B)):
        half = estimated_sunshine_statistics(_radiation_series(a + b / 2, et), et, daylight, a, b)
        assert half.monthly[0].hours_per_day.mean == pytest.approx(6.0)
        assert half.monthly[0].relative_pct == pytest.approx(50.0)
        assert half.annual_hours.mean == pytest.approx(6.0 * _DAYS_2021)
        assert half.annual_relative_pct == pytest.approx(50.0)


def test_angstrom_coefficients_are_the_calibrated_ones_with_the_classic_sum() -> None:
    assert (ANGSTROM_A, ANGSTROM_B) == (0.29, 0.49)
    assert pytest.approx(0.78) == ANGSTROM_A + ANGSTROM_B  # suma clásica de Ångström
    assert (FAO_ANGSTROM_A, FAO_ANGSTROM_B) == (0.25, 0.50)


def test_defaults_use_the_calibrated_coefficients() -> None:
    et = np.full(_DAYS_2021, 10.0)
    daylight = np.full(12, 12.0)
    series = _radiation_series(0.5, et)
    default = estimated_sunshine_statistics(series, et, daylight)
    explicit = estimated_sunshine_statistics(series, et, daylight, ANGSTROM_A, ANGSTROM_B)
    fao = estimated_sunshine_statistics(series, et, daylight, FAO_ANGSTROM_A, FAO_ANGSTROM_B)
    assert default.annual_hours.mean == explicit.annual_hours.mean
    assert default.annual_hours.mean != pytest.approx(fao.annual_hours.mean)


def test_estimated_sunshine_is_limited_to_zero_and_the_full_day() -> None:
    et = np.full(_DAYS_2021, 10.0)
    daylight = np.full(12, 12.0)
    overcast = estimated_sunshine_statistics(_radiation_series(0.1, et), et, daylight)
    clear = estimated_sunshine_statistics(_radiation_series(0.9, et), et, daylight)
    assert overcast.monthly[0].hours_per_day.mean == pytest.approx(0.0)
    assert clear.monthly[0].hours_per_day.mean == pytest.approx(12.0)
    assert clear.monthly[0].relative_pct == pytest.approx(100.0)


def test_estimated_sunshine_uses_the_extraterrestrial_energy_of_each_month() -> None:
    # La misma radiación rinde más horas de sol donde el techo es más bajo.
    et = np.concatenate([np.full(31, 5.0), np.full(_DAYS_2021 - 31, 10.0)])
    radiation = np.full(_DAYS_2021, 4.0)
    stats = estimated_sunshine_statistics(
        _series("2021-01-01", radiation_mj_m2=radiation * 3.6), et, np.full(12, 12.0)
    )
    assert stats.monthly[0].hours_per_day.mean > stats.monthly[1].hours_per_day.mean


def test_estimated_sunshine_without_radiation_or_daylight_is_none() -> None:
    et = np.full(_DAYS_2021, 10.0)
    no_radiation = estimated_sunshine_statistics(
        _series("2021-01-01", sunshine_s=et), et, np.full(12, 12.0)
    )
    assert no_radiation.monthly[0].hours_per_day.count == 0
    assert no_radiation.annual_relative_pct is None
    daylight = np.full(12, 12.0)
    daylight[0] = 0.0  # noche polar en enero
    stats = estimated_sunshine_statistics(_radiation_series(0.5, et), et, daylight)
    assert stats.monthly[0].relative_pct is None
    assert stats.monthly[1].relative_pct == pytest.approx((0.5 - ANGSTROM_A) / ANGSTROM_B * 100)
