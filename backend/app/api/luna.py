"""Endpoints de la Luna (etapa 2, ver docs/plan_tecnico.md, sección 6)."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.params import DateParam, Latitude, Longitude, NumSamples
from app.schemas.luna import (
    ApsidesResponse,
    ApsisItem,
    MoonDayResponse,
    MoonPhaseEvent,
    MoonPhasesResponse,
    MoonPositionSample,
    MoonTrajectoryResponse,
)
from app.solar.apsides import Apsis, apsides_in_year
from app.solar.events import local_day_start_jd
from app.solar.moon import apparent_position, illumination, moon_day, moon_trajectory
from app.solar.phases import MoonPhase, moon_age_days, phases_in_year
from app.solar.time import julian_century_tt

router = APIRouter()

_PHASE_KEYS = {0: "new", 1: "first_quarter", 2: "full", 3: "last_quarter"}


@router.get("/dia", response_model=MoonDayResponse)
def dia(latitude: Latitude, longitude: Longitude, date: DateParam) -> MoonDayResponse:
    """Salida, tránsito y puesta de la Luna en el día, y su fase al
    mediodía local (fracción iluminada, edad, ángulo de fase)."""
    events = moon_day(date, latitude, longitude)
    noon_jd = local_day_start_jd(date, longitude) + 0.5
    light = illumination(noon_jd)
    return MoonDayResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        rise=events.rise,
        transit=events.transit,
        set=events.set,
        transit_altitude_deg=events.transit_altitude_deg,
        always_above=events.always_above,
        illuminated_fraction=light.fraction,
        phase_angle_deg=light.phase_angle_deg,
        phase_key=light.phase_key,
        waxing=light.waxing,
        age_days=moon_age_days(noon_jd),
        bright_limb_angle_deg=light.bright_limb_angle_deg,
        distance_km=float(apparent_position(julian_century_tt(noon_jd)).distance_km),
    )


@router.get("/trayectoria", response_model=MoonTrajectoryResponse)
def trayectoria(
    latitude: Latitude,
    longitude: Longitude,
    date: DateParam,
    num_samples: NumSamples = 96,
) -> MoonTrajectoryResponse:
    """Altitud y azimut de la Luna (con paralaje, sin refracción) a lo
    largo del día solar local, para un gráfico polar."""
    result = moon_trajectory(date, latitude, longitude, num_samples)
    return MoonTrajectoryResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        illuminated_fraction=result.illuminated_fraction,
        samples=[
            MoonPositionSample(time=time, altitude=alt, azimuth=az)
            for time, alt, az in zip(result.times, result.altitude, result.azimuth, strict=True)
        ],
    )


@lru_cache(maxsize=64)
def _phases(year: int) -> tuple[MoonPhase, ...]:
    return tuple(phases_in_year(year))


@router.get("/fases", response_model=MoonPhasesResponse)
def fases(
    year: Annotated[int, Query(ge=1000, le=3000, description="Año calendario (gregoriano)")],
) -> MoonPhasesResponse:
    """Fases principales de la Luna del año (nueva, cuarto creciente, llena
    y cuarto menguante), en UT (Meeus cap. 49). No depende de la ubicación."""
    return MoonPhasesResponse(
        year=year,
        phases=[
            MoonPhaseEvent(
                kind=_PHASE_KEYS[int(phase.kind)],
                time=phase.time,
                brown_lunation=phase.brown_lunation,
            )
            for phase in _phases(year)
        ],
    )


@lru_cache(maxsize=64)
def _apsides(year: int) -> tuple[Apsis, ...]:
    return tuple(apsides_in_year(year))


@router.get("/apsides", response_model=ApsidesResponse)
def apsides(
    year: Annotated[int, Query(ge=1000, le=3000, description="Año calendario (gregoriano)")],
) -> ApsidesResponse:
    """Perigeos y apogeos de la Luna del año, con su distancia, en UT
    (Meeus cap. 50). El instante del perigeo puede errar hasta ~30 minutos."""
    return ApsidesResponse(
        year=year,
        apsides=[
            ApsisItem(
                kind=str(event.kind),
                time=event.time,
                distance_km=event.distance_km,
                parallax_arcsec=event.parallax_arcsec,
            )
            for event in _apsides(year)
        ],
    )
