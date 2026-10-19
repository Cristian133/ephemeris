from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from app.solar.coordinates import declination, right_ascension
from app.solar.events import (
    STANDARD_ALTITUDE_SUN,
    _hour_angle_at_altitude,
    daily_irradiation,
    local_day_start_jd,
    solar_noon,
    solar_transit,
    sun_trajectory,
    sunrise_sunset,
    sunrise_sunset_year,
)
from app.solar.horizontal import altitude as horizontal_altitude
from app.solar.horizontal import azimuth as horizontal_azimuth
from app.solar.horizontal import hour_angle, local_sidereal_time
from app.solar.refraction import apparent_altitude as refracted_altitude
from app.solar.time import (
    apparent_sidereal_time,
    datetime_from_julian_day,
    julian_century_tt,
    julian_day,
)

# --- Identidades exactas de las funciones auxiliares -----------------------
# El día-largo clásico: cos(H0) = -tan(latitud) * tan(declinación), con
# altitud geométrica (0°, sin refracción/semidiámetro). Independiente de
# cualquier valor numérico de tabla — son identidades trigonométricas.


def test_hour_angle_at_altitude_is_90_at_equator_regardless_of_declination() -> None:
    # En el ecuador el Sol siempre pasa 12h sobre el horizonte y 12h debajo,
    # sea cual sea su declinación (geométricamente, sin refracción).
    for declination_deg in [-23.4, 0.0, 23.4]:
        h0, always_above, always_below = _hour_angle_at_altitude(0.0, declination_deg, 0.0)
        assert h0 == pytest.approx(90.0)
        assert not always_above
        assert not always_below


def test_hour_angle_at_altitude_borderline_circumpolar() -> None:
    # latitud = declinación: el Sol roza el horizonte a medianoche (H0=180,
    # borde exacto del día polar) — identidad tan(45)*tan(45) = 1.
    h0, always_above, always_below = _hour_angle_at_altitude(45.0, 45.0, 0.0)
    assert h0 == pytest.approx(180.0)
    assert not always_above
    assert not always_below


def test_hour_angle_at_altitude_borderline_never_rises() -> None:
    # latitud = -declinación: el Sol roza el horizonte a mediodía (H0=0,
    # borde exacto de la noche polar).
    h0, always_above, always_below = _hour_angle_at_altitude(45.0, -45.0, 0.0)
    assert h0 == pytest.approx(0.0, abs=1e-4)
    assert not always_above
    assert not always_below


def test_hour_angle_at_altitude_flags_circumpolar_and_never_rises() -> None:
    _, always_above, always_below = _hour_angle_at_altitude(45.0, 46.0, 0.0)
    assert always_above and not always_below  # sol de medianoche

    _, always_above, always_below = _hour_angle_at_altitude(45.0, -46.0, 0.0)
    assert always_below and not always_above  # noche polar


def test_hour_angle_at_altitude_vectorizes_over_numpy_arrays() -> None:
    declinations = np.array([46.0, 0.0, -46.0])
    h0, always_above, always_below = _hour_angle_at_altitude(45.0, declinations, 0.0)
    assert list(always_above) == [True, False, False]
    assert list(always_below) == [False, False, True]
    assert h0[1] == pytest.approx(90.0)


# Las identidades de altitud (H=0 -> cenit, H=±90° con declinación 0 ->
# horizonte) ahora se prueban en test_horizontal.py, donde vive esa función.

# --- Comportamiento integrado (tránsito, orto/ocaso) ------------------------


@pytest.mark.parametrize(
    "day",
    [date(2024, 1, 15), date(2024, 4, 15), date(2024, 7, 15), date(2024, 10, 15)],
)
def test_transit_at_greenwich_within_equation_of_time_bound(day: date) -> None:
    # En longitud 0°, el mediodía solar difiere del mediodía UT por la
    # ecuación del tiempo, que nunca supera ~16-17 minutos en todo el año.
    transit = solar_transit(day, longitude_deg=0.0)
    noon = datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=UTC)
    assert abs((transit - noon).total_seconds()) < 20 * 60


@pytest.mark.parametrize(
    "day",
    [date(2024, 1, 15), date(2024, 4, 15), date(2024, 7, 15), date(2024, 10, 15)],
)
def test_equatorial_day_length_close_to_12_hours(day: date) -> None:
    # En el ecuador el día dura ~12h todo el año (una pequeña diferencia
    # constante por la refracción/semidiámetro de STANDARD_ALTITUDE_SUN).
    result = sunrise_sunset(day, latitude_deg=0.0, longitude_deg=0.0)
    assert result.sunrise is not None
    assert result.sunset is not None
    day_length = result.sunset - result.sunrise
    assert timedelta(hours=11, minutes=55) < day_length < timedelta(hours=12, minutes=15)


def test_sunrise_transit_sunset_are_in_order() -> None:
    # Buenos Aires, en un día cualquiera sin casos límite (polares).
    result = sunrise_sunset(date(2024, 6, 1), latitude_deg=-34.6, longitude_deg=-58.4)
    assert result.sunrise is not None
    assert result.sunset is not None
    assert result.sunrise < result.transit < result.sunset


def test_midnight_sun_near_june_solstice_at_high_latitude() -> None:
    result = sunrise_sunset(date(2024, 6, 21), latitude_deg=80.0, longitude_deg=0.0)
    assert result.sunrise is None
    assert result.sunset is None
    assert result.always_above is True


def test_polar_night_near_december_solstice_at_high_latitude() -> None:
    result = sunrise_sunset(date(2024, 12, 21), latitude_deg=80.0, longitude_deg=0.0)
    assert result.sunrise is None
    assert result.sunset is None
    assert result.always_above is False


def test_default_altitude_is_standard_altitude_sun() -> None:
    day, lat, lon = date(2024, 6, 1), -34.6, -58.4
    assert sunrise_sunset(day, lat, lon) == sunrise_sunset(day, lat, lon, STANDARD_ALTITUDE_SUN)


# --- Consistencia entre la versión escalar (un día) y la vectorizada -------
# (todo el año a la vez): deben dar exactamente el mismo resultado, porque
# ambas llaman al mismo núcleo (`_solar_transit_jd`, `_hour_angle_at_altitude`,
# `_refine_horizon_crossing`) con un jd0 escalar o con un array, respectivamente.


@pytest.mark.parametrize(
    ("latitude_deg", "longitude_deg"),
    [
        (-34.6, -58.4),  # Buenos Aires: día normal todo el año
        (80.0, 0.0),  # latitud alta: incluye sol de medianoche y noche polar
    ],
)
def test_sunrise_sunset_year_matches_day_by_day_scalar_calls(
    latitude_deg: float, longitude_deg: float
) -> None:
    year = 2024
    result = sunrise_sunset_year(year, latitude_deg, longitude_deg)
    assert len(result.dates) == 366  # 2024 es bisiesto

    sample_days_of_year = [0, 79, 171, 264, 355, 365]  # incluye 1 ene y 31 dic
    for i in sample_days_of_year:
        expected = sunrise_sunset(result.dates[i], latitude_deg, longitude_deg)
        assert result.transit[i] == expected.transit
        assert result.sunrise[i] == expected.sunrise
        assert result.sunset[i] == expected.sunset
        assert result.always_above[i] == expected.always_above


def test_sunrise_sunset_year_length_matches_calendar_year() -> None:
    assert len(sunrise_sunset_year(2023, 0.0, 0.0).dates) == 365  # no bisiesto
    assert len(sunrise_sunset_year(2024, 0.0, 0.0).dates) == 366  # bisiesto


# --- sun_trajectory ----------------------------------------------------


def test_sun_trajectory_covers_24h_at_requested_resolution() -> None:
    day = date(2024, 6, 1)
    result = sun_trajectory(day, latitude_deg=-34.6, longitude_deg=-58.4, num_samples=96)

    assert len(result.times) == 96
    assert len(result.altitude) == 96
    assert len(result.apparent_altitude) == 96
    assert len(result.azimuth) == 96
    # Parte de la medianoche media local (0h UT + 58.4/15 h) y el último
    # instante es 15' antes de la siguiente (24h/96).
    start = datetime_from_julian_day(local_day_start_jd(day, -58.4))
    assert result.times[0] == start
    assert result.times[0] == datetime(2024, 6, 1, 3, 53, 36, tzinfo=UTC)
    assert result.times[-1] == start + timedelta(hours=23, minutes=45)


def test_sun_trajectory_matches_manual_composition_of_public_functions() -> None:
    # Regresión: sun_trajectory no es más que componer coordinates.py y
    # horizontal.py directamente en cada instante muestreado.
    day = date(2024, 3, 20)
    lat, lon = 40.4, -3.7
    result = sun_trajectory(day, lat, lon, num_samples=48)

    for i, time in enumerate(result.times):
        jd = julian_day(time)
        t = julian_century_tt(jd)
        alpha = right_ascension(t)
        delta = declination(t)
        lst = local_sidereal_time(apparent_sidereal_time(jd), lon)
        h = hour_angle(lst, alpha)

        assert result.altitude[i] == pytest.approx(horizontal_altitude(lat, delta, h))
        assert result.apparent_altitude[i] == pytest.approx(refracted_altitude(result.altitude[i]))
        assert result.azimuth[i] == pytest.approx(horizontal_azimuth(lat, delta, h))


def test_sun_trajectory_max_altitude_near_solar_transit() -> None:
    day = date(2024, 3, 20)
    lat, lon = 40.4, -3.7
    num_samples = 96
    result = sun_trajectory(day, lat, lon, num_samples=num_samples)

    transit = solar_transit(day, lon)
    peak_time = result.times[max(range(num_samples), key=lambda i: result.altitude[i])]

    sampling_step = timedelta(hours=24 / num_samples)
    assert abs((peak_time - transit).total_seconds()) <= sampling_step.total_seconds()


# --- solar_noon ----------------------------------------------------------


def test_solar_noon_transit_matches_solar_transit() -> None:
    day, lon = date(2024, 3, 20), -3.7
    assert solar_noon(day, latitude_deg=40.4, longitude_deg=lon).transit == solar_transit(day, lon)


def test_solar_noon_altitude_matches_sun_trajectory_peak() -> None:
    # Regresión cruzada: la altitud de mediodía debe ser (casi) el máximo
    # de la trayectoria muestreada del mismo día.
    day, lat, lon = date(2024, 3, 20), 40.4, -3.7
    noon = solar_noon(day, lat, lon)
    trajectory = sun_trajectory(day, lat, lon, num_samples=288)
    assert noon.altitude_deg == pytest.approx(max(trajectory.altitude), abs=0.05)


def test_solar_noon_apparent_altitude_matches_refraction_module() -> None:
    day, lat, lon = date(2024, 3, 20), 40.4, -3.7
    noon = solar_noon(day, lat, lon)
    assert noon.apparent_altitude_deg == pytest.approx(refracted_altitude(noon.altitude_deg))


def test_solar_noon_apparent_altitude_is_above_true_altitude_near_horizon() -> None:
    # A alta latitud en invierno el sol de mediodía está bajo, donde la
    # refracción es más notoria: la altitud aparente debe ser mayor.
    noon = solar_noon(date(2024, 12, 21), latitude_deg=65.0, longitude_deg=0.0)
    assert noon.apparent_altitude_deg > noon.altitude_deg


def test_solar_noon_azimuth_is_north_when_latitude_less_than_declination() -> None:
    # Mismo hecho que en test_horizontal.py: Buenos Aires en diciembre,
    # el sol de mediodía queda al Norte.
    noon = solar_noon(date(2024, 12, 21), latitude_deg=-34.6, longitude_deg=-58.4)
    assert noon.azimuth_deg == pytest.approx(0.0, abs=1e-6)


def test_solar_noon_azimuth_is_south_when_latitude_greater_than_declination() -> None:
    noon = solar_noon(date(2024, 6, 21), latitude_deg=40.4, longitude_deg=-3.7)
    assert noon.azimuth_deg == pytest.approx(180.0, abs=1e-6)


# --- daily_irradiation -----------------------------------------------------


def test_daily_irradiation_matches_requested_sample_count() -> None:
    result = daily_irradiation(date(2024, 6, 1), -34.6, -58.4, num_samples=48)
    assert len(result.times) == 48
    assert len(result.power_w_per_m2) == 48


def test_daily_irradiation_power_is_zero_at_night_and_positive_by_day() -> None:
    result = daily_irradiation(date(2024, 6, 1), -34.6, -58.4, num_samples=96)
    assert any(p == 0.0 for p in result.power_w_per_m2)  # de noche
    assert any(p > 0.0 for p in result.power_w_per_m2)  # de día


def test_daily_irradiation_energy_is_positive() -> None:
    result = daily_irradiation(date(2024, 6, 1), -34.6, -58.4)
    assert result.energy_wh_per_m2 > 0


def test_daily_irradiation_energy_higher_in_summer_than_winter() -> None:
    # Buenos Aires: más energía en el verano austral (diciembre) que en
    # el invierno (junio) — días más largos y sol más alto.
    summer = daily_irradiation(date(2024, 12, 21), -34.6, -58.4)
    winter = daily_irradiation(date(2024, 6, 21), -34.6, -58.4)
    assert summer.energy_wh_per_m2 > winter.energy_wh_per_m2


def test_daily_irradiation_energy_higher_at_equator_than_high_latitude_on_equinox() -> None:
    # En el equinoccio, el sol pasa más alto en el cielo (menos masa de
    # aire, menos pérdida geométrica) en el ecuador que a alta latitud.
    equator = daily_irradiation(date(2024, 3, 20), 0.0, 0.0)
    high_latitude = daily_irradiation(date(2024, 3, 20), 60.0, 0.0)
    assert equator.energy_wh_per_m2 > high_latitude.energy_wh_per_m2


def test_daily_irradiation_zero_during_polar_night() -> None:
    result = daily_irradiation(date(2024, 12, 21), 80.0, 0.0, num_samples=48)
    assert all(p == 0.0 for p in result.power_w_per_m2)
    assert result.energy_wh_per_m2 == 0.0


# --- Día solar local (longitudes lejanas a Greenwich) ----------------------


def test_local_day_start_is_local_mean_midnight() -> None:
    assert datetime_from_julian_day(local_day_start_jd(date(2024, 6, 1), 0.0)) == datetime(
        2024, 6, 1, tzinfo=UTC
    )
    # 90° al este: la medianoche media local es 6h antes de 0h UT.
    assert datetime_from_julian_day(local_day_start_jd(date(2024, 6, 1), 90.0)) == datetime(
        2024, 5, 31, 18, tzinfo=UTC
    )


@pytest.mark.parametrize("longitude", [-170.0, -58.4, 0.0, 100.0, 151.2, 179.0])
def test_daily_irradiation_energy_does_not_depend_on_longitude(longitude: float) -> None:
    """La energía de un día solar depende de la latitud y la fecha, no de
    la longitud. Con ventanas de 24h desde 0h UT, el amanecer a longitudes
    al este de ~+90° quedaba fuera de la ventana y la energía se
    subestimaba mucho."""
    reference = daily_irradiation(date(2024, 3, 20), -34.0, 0.0).energy_wh_per_m2
    result = daily_irradiation(date(2024, 3, 20), -34.0, longitude).energy_wh_per_m2
    assert result == pytest.approx(reference, rel=0.01)


def test_sun_trajectory_includes_the_whole_daylight_at_far_east_longitudes() -> None:
    # Sídney: el orto cae el día UT anterior; la trayectoria del día local
    # debe empezar de noche, subir por encima del horizonte y terminar de noche.
    result = sun_trajectory(date(2024, 1, 15), -33.9, 151.2)
    assert result.altitude[0] < 0
    assert max(result.altitude) > 60
    assert result.altitude[-1] < 0


def test_sun_trajectory_peak_matches_transit_at_far_east_longitude() -> None:
    day, lat, lon = date(2024, 1, 15), -33.9, 151.2
    result = sun_trajectory(day, lat, lon, num_samples=288)
    peak = result.times[max(range(288), key=lambda i: result.altitude[i])]
    assert abs((peak - solar_transit(day, lon)).total_seconds()) <= 24 * 3600 / 288


# --- Refracción configurable ----------------------------------------------


def test_solar_noon_refraction_follows_pressure_and_temperature() -> None:
    day, lat, lon = date(2024, 12, 21), 65.0, 0.0  # sol bajo: la refracción se nota
    standard = solar_noon(day, lat, lon)
    cold_high_pressure = solar_noon(day, lat, lon, pressure_mbar=1040.0, temperature_c=-20.0)
    thin_air = solar_noon(day, lat, lon, pressure_mbar=700.0, temperature_c=10.0)
    assert cold_high_pressure.apparent_altitude_deg > standard.apparent_altitude_deg
    assert thin_air.apparent_altitude_deg < standard.apparent_altitude_deg
    assert cold_high_pressure.altitude_deg == standard.altitude_deg  # la verdadera no cambia


def test_sun_trajectory_refraction_follows_pressure_and_temperature() -> None:
    standard = sun_trajectory(date(2024, 6, 1), 40.0, 0.0)
    thin_air = sun_trajectory(date(2024, 6, 1), 40.0, 0.0, pressure_mbar=700.0)
    assert thin_air.altitude == standard.altitude
    assert thin_air.apparent_altitude != standard.apparent_altitude


# --- Irradiancia: componentes ---------------------------------------------


def test_daily_irradiation_components_add_up() -> None:
    result = daily_irradiation(date(2024, 6, 21), 40.0, -3.7)
    for total, direct, diffuse in zip(
        result.power_w_per_m2, result.direct_w_per_m2, result.diffuse_w_per_m2, strict=True
    ):
        assert total == pytest.approx(direct + diffuse)
    assert result.energy_wh_per_m2 == pytest.approx(
        result.direct_energy_wh_per_m2 + result.diffuse_energy_wh_per_m2, rel=1e-9
    )
    assert 0.05 < result.diffuse_energy_wh_per_m2 / result.energy_wh_per_m2 < 0.30


def test_daily_irradiation_clear_sky_summer_energy_is_plausible() -> None:
    # Madrid en el solsticio de verano: ~8-9 kWh/m² por día en cielo despejado.
    result = daily_irradiation(date(2024, 6, 21), 40.4, -3.7)
    assert 7000 < result.energy_wh_per_m2 < 10000


def test_daily_irradiation_elevation_and_turbidity_change_energy() -> None:
    base = daily_irradiation(date(2024, 6, 21), 40.0, 0.0).energy_wh_per_m2
    mountain = daily_irradiation(date(2024, 6, 21), 40.0, 0.0, elevation_m=3000.0)
    hazy = daily_irradiation(date(2024, 6, 21), 40.0, 0.0, linke_turbidity=6.0)
    assert mountain.energy_wh_per_m2 > base
    assert hazy.energy_wh_per_m2 < base
