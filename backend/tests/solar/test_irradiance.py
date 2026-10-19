import numpy as np
import pytest

from app.solar.irradiance import (
    SOLAR_CONSTANT,
    air_mass,
    clear_sky_components,
    extraterrestrial_irradiance,
    pressure_ratio,
)


def test_extraterrestrial_irradiance_at_one_au_equals_solar_constant() -> None:
    assert extraterrestrial_irradiance(1.0) == pytest.approx(SOLAR_CONSTANT)


def test_extraterrestrial_irradiance_scales_as_inverse_square() -> None:
    assert extraterrestrial_irradiance(2.0) == pytest.approx(SOLAR_CONSTANT / 4)


def test_air_mass_is_approximately_1_at_zenith() -> None:
    # AM=1 exacto en el cenit es la definición idealizada (trayecto vertical
    # mínimo); Kasten-Young da un valor levemente distinto por su término de
    # corrección empírico.
    assert air_mass(90.0) == pytest.approx(1.0, abs=0.001)


def test_air_mass_is_approximately_1_5_at_standard_test_condition_angle() -> None:
    # AM1.5 (48.19° de ángulo cenital) es la condición estándar de la
    # industria fotovoltaica (STC) para especificar paneles solares — un
    # hecho de conocimiento general, no un valor de tabla de este proyecto.
    zenith_deg = 48.19
    assert air_mass(90.0 - zenith_deg) == pytest.approx(1.5, abs=0.01)


def test_air_mass_increases_as_sun_approaches_horizon() -> None:
    assert air_mass(80.0) < air_mass(45.0) < air_mass(20.0) < air_mass(5.0)


def test_pressure_ratio_is_one_at_sea_level_and_drops_with_elevation() -> None:
    assert pressure_ratio(0.0) == pytest.approx(1.0)
    # Atmósfera estándar: ~795 hPa a 2000 m (hecho de conocimiento general).
    assert pressure_ratio(2000.0) * 1013.25 == pytest.approx(795, abs=3)


def test_components_are_zero_at_and_below_horizon() -> None:
    for altitude_deg in (0.0, -10.0, -70.0):  # -70: no debe dar NaN
        for component in clear_sky_components(altitude_deg, 1.0):
            assert component == 0.0


def test_components_at_zenith_are_plausible_clear_sky_values() -> None:
    # Cielo despejado a nivel del mar, cenit: directa ~900-1000 W/m², global
    # ~1000-1100 y difusa 10-15% del total (órdenes de magnitud bien conocidos).
    dni, dhi, ghi = clear_sky_components(90.0, 1.0)
    assert 900 < dni < 1000
    assert 1000 < ghi < 1100
    assert 0.08 < dhi / ghi < 0.15


def test_global_equals_projected_direct_plus_diffuse() -> None:
    for altitude_deg in (5.0, 30.0, 60.0, 90.0):
        dni, dhi, ghi = clear_sky_components(altitude_deg, 1.0)
        assert ghi == pytest.approx(dni * np.sin(np.radians(altitude_deg)) + dhi)
        assert dhi >= 0


def test_global_increases_with_altitude() -> None:
    values = [clear_sky_components(h, 1.0)[2] for h in (10.0, 45.0, 90.0)]
    assert values == sorted(values)


def test_more_turbidity_means_less_direct_and_more_share_of_diffuse() -> None:
    clear = clear_sky_components(45.0, 1.0, linke_turbidity=2.0)
    hazy = clear_sky_components(45.0, 1.0, linke_turbidity=6.0)
    assert hazy[0] < clear[0]
    assert hazy[2] < clear[2]
    assert hazy[1] / hazy[2] > clear[1] / clear[2]


def test_higher_elevation_means_more_direct_irradiance() -> None:
    sea = clear_sky_components(45.0, 1.0, elevation_m=0.0)
    mountain = clear_sky_components(45.0, 1.0, elevation_m=3000.0)
    assert mountain[0] > sea[0]


def test_components_scale_with_inverse_square_of_distance() -> None:
    near = clear_sky_components(45.0, 0.98)
    far = clear_sky_components(45.0, 1.02)
    for n, f in zip(near, far, strict=True):
        assert n / f == pytest.approx((1.02 / 0.98) ** 2)


def test_functions_vectorize_over_numpy_arrays() -> None:
    altitudes = np.array([-10.0, 0.0, 30.0, 90.0])
    radii = np.full_like(altitudes, 1.0)
    dni, dhi, ghi = clear_sky_components(altitudes, radii)
    assert list(ghi[:2]) == [0.0, 0.0]
    assert list(dni[:2]) == [0.0, 0.0]
    assert list(dhi[:2]) == [0.0, 0.0]
    assert ghi[2] > 0
    assert ghi[3] == pytest.approx(clear_sky_components(90.0, 1.0)[2])
