"""Endpoints de `/sol` (ver docs/plan_tecnico.md, sección 5)."""

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.sol import (
    AltitudeCrossing,
    AnnualSunResponse,
    DailySun,
    DailySunResponse,
    IrradianceResponse,
    IrradianceSample,
    PanelResponse,
    SeasonsResponse,
    SolarNoonResponse,
    SunPosition,
    TiltEnergy,
    TrajectoryResponse,
    TwilightResponse,
)
from app.solar.events import (
    daily_irradiation,
    solar_noon,
    sun_trajectory,
    sunrise_sunset,
    sunrise_sunset_year,
)
from app.solar.panel import optimal_panel_orientation
from app.solar.seasons import MAX_YEAR, MIN_YEAR, seasons
from app.solar.twilight import twilight

router = APIRouter()

_MIN_SAMPLES = 24
_MAX_SAMPLES = 288

Latitude = Annotated[float, Query(ge=-90, le=90, description="Latitud del observador, en grados")]
Longitude = Annotated[
    float,
    Query(ge=-180, le=180, description="Longitud del observador, en grados (positiva al este)"),
]
DateParam = Annotated[date_type, Query(description="Fecha (UTC)")]
NumSamples = Annotated[
    int,
    Query(
        ge=_MIN_SAMPLES,
        le=_MAX_SAMPLES,
        description="Cantidad de instantes a muestrear a lo largo del día (equiespaciados)",
    ),
]


@router.get("/anual", response_model=AnnualSunResponse)
def anual(
    latitude: Latitude,
    longitude: Longitude,
    year: Annotated[int, Query(ge=1, le=9999, description="Año calendario (gregoriano)")],
) -> AnnualSunResponse:
    """Evolución anual de las horas de sol (punto 2) para una ubicación
    dada — orto, tránsito, ocaso y duración del día para cada día del año.
    """
    result = sunrise_sunset_year(year, latitude, longitude)

    days = [
        DailySun(
            date=day,
            transit=transit,
            sunrise=sunrise,
            sunset=sunset,
            day_length_hours=(
                (sunset - sunrise).total_seconds() / 3600 if sunrise and sunset else None
            ),
            always_above=always_above,
        )
        for day, transit, sunrise, sunset, always_above in zip(
            result.dates,
            result.transit,
            result.sunrise,
            result.sunset,
            result.always_above,
            strict=True,
        )
    ]

    return AnnualSunResponse(latitude=latitude, longitude=longitude, year=year, days=days)


@router.get("/dia", response_model=DailySunResponse)
def dia(latitude: Latitude, longitude: Longitude, date: DateParam) -> DailySunResponse:
    """Horas de sol en un día (punto 1): orto, tránsito, ocaso y duración
    del día para una ubicación y fecha dadas."""
    result = sunrise_sunset(date, latitude, longitude)
    day_length_hours = (
        (result.sunset - result.sunrise).total_seconds() / 3600
        if result.sunrise and result.sunset
        else None
    )
    return DailySunResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        transit=result.transit,
        sunrise=result.sunrise,
        sunset=result.sunset,
        day_length_hours=day_length_hours,
        always_above=result.always_above,
    )


@router.get("/mediodia", response_model=SolarNoonResponse)
def mediodia(latitude: Latitude, longitude: Longitude, date: DateParam) -> SolarNoonResponse:
    """Mediodía solar e inclinación del Sol en ese instante (punto 4):
    altitud máxima del día y azimut (0°=Norte o 180°=Sur)."""
    result = solar_noon(date, latitude, longitude)
    return SolarNoonResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        transit=result.transit,
        altitude_deg=result.altitude_deg,
        apparent_altitude_deg=result.apparent_altitude_deg,
        azimuth_deg=result.azimuth_deg,
    )


@router.get("/trayectoria", response_model=TrajectoryResponse)
def trayectoria(
    latitude: Latitude,
    longitude: Longitude,
    date: DateParam,
    num_samples: NumSamples = 96,
) -> TrajectoryResponse:
    """Trayectoria del Sol (altitud/azimut) a lo largo de un día (punto 3),
    para un gráfico polar. Incluye las 24h del día, no solo las horas de
    luz — el cliente filtra por altitud si solo quiere el tramo diurno.
    """
    result = sun_trajectory(date, latitude, longitude, num_samples)

    samples = [
        SunPosition(time=time, altitude=alt, apparent_altitude=apparent_alt, azimuth=az)
        for time, alt, apparent_alt, az in zip(
            result.times, result.altitude, result.apparent_altitude, result.azimuth, strict=True
        )
    ]

    return TrajectoryResponse(latitude=latitude, longitude=longitude, date=date, samples=samples)


@router.get("/irradiancia", response_model=IrradianceResponse)
def irradiancia(
    latitude: Latitude,
    longitude: Longitude,
    date: DateParam,
    num_samples: NumSamples = 96,
) -> IrradianceResponse:
    """Irradiancia solar en cielo despejado a lo largo de un día (punto 5)
    y la energía total recibida por m² en el día. Modelo teórico
    simplificado (ver `app.solar.irradiance`): no tiene en cuenta nubosidad
    real ni componente difusa.
    """
    result = daily_irradiation(date, latitude, longitude, num_samples)

    samples = [
        IrradianceSample(time=time, power_w_per_m2=power)
        for time, power in zip(result.times, result.power_w_per_m2, strict=True)
    ]

    return IrradianceResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        energy_wh_per_m2=result.energy_wh_per_m2,
        samples=samples,
    )


@router.get("/crepusculos", response_model=TwilightResponse)
def crepusculos(latitude: Latitude, longitude: Longitude, date: DateParam) -> TwilightResponse:
    """Crepúsculos (civil, náutico, astronómico) y límites de las horas azul
    y dorada para una ubicación y fecha dadas."""
    result = twilight(date, latitude, longitude)
    return TwilightResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        astronomical=AltitudeCrossing(**vars(result.astronomical)),
        nautical=AltitudeCrossing(**vars(result.nautical)),
        civil=AltitudeCrossing(**vars(result.civil)),
        blue_hour_limit=AltitudeCrossing(**vars(result.blue_hour_limit)),
        horizon=AltitudeCrossing(**vars(result.horizon)),
        golden_hour_limit=AltitudeCrossing(**vars(result.golden_hour_limit)),
    )


@router.get("/estaciones", response_model=SeasonsResponse)
def estaciones(
    year: Annotated[
        int, Query(ge=MIN_YEAR, le=MAX_YEAR, description="Año calendario (gregoriano)")
    ],
) -> SeasonsResponse:
    """Equinoccios y solsticios del año (Meeus cap. 27). No depende de la
    ubicación."""
    result = seasons(year)
    return SeasonsResponse(year=year, **vars(result))


@router.get("/panel", response_model=PanelResponse)
def panel(
    latitude: Latitude,
    longitude: Longitude,
    year: Annotated[int, Query(ge=1, le=9999, description="Año calendario (gregoriano)")],
) -> PanelResponse:
    """Orientación e inclinación óptimas de un panel solar fijo: la que más
    energía acumula en el año (y en cada solsticio), en cielo despejado.
    Modelo simplificado (ver `app.solar.panel`)."""
    result = optimal_panel_orientation(year, latitude, longitude)
    return PanelResponse(
        latitude=latitude,
        longitude=longitude,
        year=year,
        azimuth_deg=result.azimuth_deg,
        annual_tilt_deg=result.annual_tilt_deg,
        winter_tilt_deg=result.winter_tilt_deg,
        summer_tilt_deg=result.summer_tilt_deg,
        annual_kwh_per_m2=result.annual_kwh_per_m2,
        horizontal_kwh_per_m2=result.horizontal_kwh_per_m2,
        curve=[TiltEnergy(tilt_deg=t, annual_kwh_per_m2=e) for t, e in result.curve],
    )
