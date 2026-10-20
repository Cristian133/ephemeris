from datetime import date

import numpy as np
import pytest

from app.solar.events import daily_irradiation
from app.solar.insolation import clear_sky_daily_ghi_kwh, extraterrestrial_daily_kwh


def test_one_value_per_day_of_the_year() -> None:
    assert clear_sky_daily_ghi_kwh(2021, -34.5, -58.5).shape == (365,)
    assert clear_sky_daily_ghi_kwh(2024, -34.5, -58.5).shape == (366,)


def test_matches_the_single_day_calculation() -> None:
    # Misma cadena de cálculo que `daily_irradiation`: debe coincidir con ella.
    year = clear_sky_daily_ghi_kwh(2021, -34.5, -58.5)
    for day in (date(2021, 1, 15), date(2021, 6, 21), date(2021, 12, 21)):
        expected = daily_irradiation(day, -34.5, -58.5, num_samples=96).energy_wh_per_m2 / 1000
        assert year[day.timetuple().tm_yday - 1] == pytest.approx(expected, rel=0.01)


def test_seasons_follow_the_hemisphere() -> None:
    south = clear_sky_daily_ghi_kwh(2021, -34.5, -58.5)
    north = clear_sky_daily_ghi_kwh(2021, 40.0, -3.7)
    assert south[354] > 2 * south[171]  # 21 dic frente a 21 jun
    assert north[171] > 2 * north[354]


def test_clear_sky_day_energy_and_annual_total_are_plausible() -> None:
    daily = clear_sky_daily_ghi_kwh(2021, -34.5, -58.5)
    assert 8.0 < daily.max() < 9.5  # verano de latitud media: ~8-9 kWh/m²
    assert 2000 < daily.sum() < 2300  # kWh/m² al año con cielo despejado


def test_higher_turbidity_and_lower_altitude_both_reduce_the_energy() -> None:
    clean = clear_sky_daily_ghi_kwh(2021, 40.0, -3.7, 0.0, 2.0).sum()
    hazy = clear_sky_daily_ghi_kwh(2021, 40.0, -3.7, 0.0, 6.0).sum()
    mountain = clear_sky_daily_ghi_kwh(2021, 40.0, -3.7, 3000.0, 2.0).sum()
    assert hazy < clean < mountain


def test_polar_night_has_no_energy() -> None:
    daily = clear_sky_daily_ghi_kwh(2021, 80.0, 0.0)
    assert daily[354] == pytest.approx(0.0, abs=1e-6)
    assert daily[171] > 4.0
    assert not np.isnan(daily).any()


def test_extraterrestrial_energy_matches_textbook_values() -> None:
    equator = extraterrestrial_daily_kwh(2021, 0.0, 0.0)
    assert equator.shape == (365,)
    assert equator.mean() == pytest.approx(10.0, abs=0.15)  # ~10 kWh/m² por día en el ecuador
    south = extraterrestrial_daily_kwh(2021, -34.5, -58.5)
    assert south[354] == pytest.approx(12.3, abs=0.3)  # 21 de diciembre a 35°S
    assert south[171] == pytest.approx(4.4, abs=0.3)  # 21 de junio


def test_extraterrestrial_is_the_ceiling_of_clear_sky() -> None:
    for latitude in (-34.5, 0.0, 40.0):
        ceiling = extraterrestrial_daily_kwh(2021, latitude, 0.0)
        clear = clear_sky_daily_ghi_kwh(2021, latitude, 0.0)
        assert np.all(clear <= ceiling + 1e-9)
        sunny = ceiling > 1.0
        assert (clear[sunny] / ceiling[sunny]).min() > 0.5 and (
            clear[sunny] / ceiling[sunny]
        ).max() < 0.85


def test_extraterrestrial_polar_night_is_zero_and_never_nan() -> None:
    daily = extraterrestrial_daily_kwh(2021, 80.0, 0.0)
    assert daily[354] == pytest.approx(0.0, abs=1e-9)
    assert not np.isnan(daily).any()
