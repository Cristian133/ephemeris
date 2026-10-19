from datetime import UTC, datetime, timedelta

import pytest

from app.solar.seasons import seasons

# Instantes publicados (USNO/almanaques) de los equinoccios y solsticios de
# 2024, redondeados al minuto y en UT. La tolerancia cubre ΔT (~69 s en
# 2024, no modelado en esta app) y el redondeo al minuto.
_TOLERANCE = timedelta(minutes=3)


def test_seasons_2024_match_published_instants() -> None:
    result = seasons(2024)
    assert abs(result.march_equinox - datetime(2024, 3, 20, 3, 6, tzinfo=UTC)) < _TOLERANCE
    assert abs(result.june_solstice - datetime(2024, 6, 20, 20, 51, tzinfo=UTC)) < _TOLERANCE
    assert abs(result.september_equinox - datetime(2024, 9, 22, 12, 44, tzinfo=UTC)) < _TOLERANCE
    assert abs(result.december_solstice - datetime(2024, 12, 21, 9, 21, tzinfo=UTC)) < _TOLERANCE


def test_seasons_are_in_chronological_order() -> None:
    result = seasons(2030)
    ordered = [
        result.march_equinox,
        result.june_solstice,
        result.september_equinox,
        result.december_solstice,
    ]
    assert ordered == sorted(ordered)
    assert all(moment.year == 2030 for moment in ordered)


@pytest.mark.parametrize("year", [999, 3001])
def test_seasons_rejects_years_outside_algorithm_range(year: int) -> None:
    with pytest.raises(ValueError):
        seasons(year)
