from datetime import date

import pytest

from app.solar.twilight import twilight

_BUENOS_AIRES = (-34.6, -58.4)


def test_twilight_phases_are_ordered_around_sunrise_and_sunset() -> None:
    result = twilight(date(2024, 3, 20), *_BUENOS_AIRES)
    morning = [
        result.astronomical.rise,
        result.nautical.rise,
        result.civil.rise,
        result.blue_hour_limit.rise,
        result.horizon.rise,
        result.golden_hour_limit.rise,
    ]
    evening = [
        result.golden_hour_limit.set,
        result.horizon.set,
        result.blue_hour_limit.set,
        result.civil.set,
        result.nautical.set,
        result.astronomical.set,
    ]
    assert all(moment is not None for moment in morning + evening)
    assert morning == sorted(morning)
    assert evening == sorted(evening)
    assert morning[-1] < evening[0]


def test_civil_twilight_lasts_roughly_half_hour_at_equinox_mid_latitude() -> None:
    result = twilight(date(2024, 3, 20), *_BUENOS_AIRES)
    minutes = (result.horizon.rise - result.civil.rise).total_seconds() / 60
    assert 24 < minutes < 36


def test_twilight_at_equator_is_shorter_than_at_high_latitude() -> None:
    equator = twilight(date(2024, 3, 20), 0.0, 0.0)
    north = twilight(date(2024, 3, 20), 60.0, 0.0)
    equator_minutes = (equator.horizon.rise - equator.civil.rise).total_seconds() / 60
    north_minutes = (north.horizon.rise - north.civil.rise).total_seconds() / 60
    assert equator_minutes < north_minutes


def test_astronomical_twilight_never_ends_in_high_latitude_summer() -> None:
    # A 60°N en el solsticio de junio el Sol no baja de -18° - 6° = -6.6°
    # (90 - 60 - 23.4): no hay noche astronómica ni náutica.
    result = twilight(date(2024, 6, 21), 60.0, 0.0)
    assert result.astronomical.rise is None
    assert result.astronomical.always_above is True
    assert result.nautical.always_above is True
    assert result.civil.rise is not None
    assert result.civil.always_above is None


def test_crossing_records_requested_altitude() -> None:
    result = twilight(date(2024, 3, 20), *_BUENOS_AIRES)
    assert result.civil.altitude_deg == pytest.approx(-6.0)
    assert result.golden_hour_limit.altitude_deg == pytest.approx(6.0)
