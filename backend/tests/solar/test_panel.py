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
