import pytest

from app.meteo.grid import Cell, cell_for


def test_cell_center_is_a_multiple_of_the_resolution() -> None:
    cell = cell_for(-34.6037, -58.3816)  # Buenos Aires
    assert cell.latitude == pytest.approx(-34.5)
    assert cell.longitude == pytest.approx(-58.5)


def test_nearby_points_share_a_cell_and_distant_ones_do_not() -> None:
    assert cell_for(-34.60, -58.38) == cell_for(-34.55, -58.45)
    assert cell_for(-34.60, -58.38) != cell_for(-34.80, -58.38)


def test_ties_round_up_instead_of_to_even() -> None:
    # 0.125 es el límite entre las celdas 0 y 1: debe ir siempre a la misma.
    assert cell_for(0.125, 0.125) == Cell(1, 1)
    assert cell_for(0.375, 0.375) == Cell(2, 2)


def test_antimeridian_is_a_single_meridian() -> None:
    assert cell_for(0.0, 180.0) == cell_for(0.0, -180.0)
    assert cell_for(0.0, -180.0).longitude == pytest.approx(-180.0)


def test_poles_are_valid_cells() -> None:
    assert cell_for(90.0, 0.0).latitude == pytest.approx(90.0)
    assert cell_for(-90.0, 0.0).latitude == pytest.approx(-90.0)
