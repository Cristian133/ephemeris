import pytest

from app.solar.panel import optimal_panel_orientation


def test_panel_faces_the_equator() -> None:
    assert optimal_panel_orientation(2024, -34.6, -58.4).azimuth_deg == 0.0  # mira al norte
    assert optimal_panel_orientation(2024, 40.4, -3.7).azimuth_deg == 180.0  # mira al sur


def test_annual_tilt_is_close_to_latitude_at_mid_latitudes() -> None:
    for latitude in (-34.6, 40.4):
        result = optimal_panel_orientation(2024, latitude, 0.0)
        assert result.annual_tilt_deg == pytest.approx(abs(latitude), abs=12)


def test_winter_tilt_is_steeper_than_summer_tilt() -> None:
    for latitude in (-34.6, 40.4):
        result = optimal_panel_orientation(2024, latitude, 0.0)
        assert result.winter_tilt_deg > result.annual_tilt_deg > result.summer_tilt_deg


def test_optimum_beats_horizontal_panel_and_curve_peaks_near_it() -> None:
    result = optimal_panel_orientation(2024, -34.6, -58.4)
    assert result.annual_kwh_per_m2 > result.horizontal_kwh_per_m2
    best_on_curve = max(result.curve, key=lambda point: point[1])
    assert abs(best_on_curve[0] - result.annual_tilt_deg) <= 5
    assert [tilt for tilt, _ in result.curve] == list(range(0, 91, 5))


def test_equatorial_panel_is_nearly_flat() -> None:
    assert optimal_panel_orientation(2024, 0.0, 0.0).annual_tilt_deg <= 10


def test_albedo_pushes_the_optimum_towards_steeper_tilts() -> None:
    dark = optimal_panel_orientation(2024, 46.0, 7.0, albedo=0.0)
    snow = optimal_panel_orientation(2024, 46.0, 7.0, albedo=0.9)
    assert snow.annual_tilt_deg >= dark.annual_tilt_deg
    assert snow.annual_kwh_per_m2 > dark.annual_kwh_per_m2


def test_diffuse_light_makes_the_horizontal_panel_less_bad() -> None:
    # Con aire turbio (mucha difusa, que llega de toda la bóveda) el óptimo
    # se acerca a la horizontal respecto a aire muy limpio.
    clean = optimal_panel_orientation(2024, 40.4, -3.7, linke_turbidity=1.5)
    hazy = optimal_panel_orientation(2024, 40.4, -3.7, linke_turbidity=7.0)
    assert hazy.annual_tilt_deg <= clean.annual_tilt_deg
    assert hazy.horizontal_kwh_per_m2 / hazy.annual_kwh_per_m2 > (
        clean.horizontal_kwh_per_m2 / clean.annual_kwh_per_m2
    )


def test_annual_energy_is_plausible_for_clear_sky() -> None:
    # Madrid con panel óptimo y cielo despejado: ~2000-2500 kWh/m²/año
    # (la realidad con nubes ronda 1900; despejado teórico es mayor).
    result = optimal_panel_orientation(2024, 40.4, -3.7)
    assert 1800 < result.annual_kwh_per_m2 < 2800


def test_annual_energy_does_not_depend_on_longitude() -> None:
    reference = optimal_panel_orientation(2024, -34.6, 0.0)
    east = optimal_panel_orientation(2024, -34.6, 151.0)
    assert east.annual_kwh_per_m2 == pytest.approx(reference.annual_kwh_per_m2, rel=0.01)
    assert east.annual_tilt_deg == pytest.approx(reference.annual_tilt_deg, abs=3)


def test_monthly_energy_adds_up_to_the_annual_total_and_follows_the_seasons() -> None:
    south = optimal_panel_orientation(2021, -34.6, -58.4)
    assert len(south.monthly_kwh_per_m2) == 12
    assert sum(south.monthly_kwh_per_m2) == pytest.approx(south.annual_kwh_per_m2, rel=0.03)
    assert south.monthly_kwh_per_m2[11] > south.monthly_kwh_per_m2[5]  # diciembre sobre junio
    north = optimal_panel_orientation(2021, 40.4, -3.7)
    assert north.monthly_kwh_per_m2[5] > north.monthly_kwh_per_m2[11]
