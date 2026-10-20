"""Endpoints de eclipses (etapa 2)."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.luna import EclipsesResponse, LunarEclipseItem, SolarEclipseItem
from app.solar.eclipses import LunarEclipse, SolarEclipse, eclipses_in_year
from app.solar.moon import moon_altitude
from app.solar.time import julian_day

router = APIRouter()


@lru_cache(maxsize=64)
def _eclipses(year: int) -> tuple[tuple[SolarEclipse, ...], tuple[LunarEclipse, ...]]:
    solar, lunar = eclipses_in_year(year)
    return tuple(solar), tuple(lunar)


@router.get("/anio", response_model=EclipsesResponse)
def anio(
    year: Annotated[int, Query(ge=1800, le=2200, description="Año calendario (gregoriano)")],
    latitude: Annotated[
        float | None,
        Query(ge=-90, le=90, description="Latitud, para saber si el eclipse lunar se ve"),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(ge=-180, le=180, description="Longitud (positiva al este)"),
    ] = None,
) -> EclipsesResponse:
    """Eclipses de Sol y de Luna del año (Meeus cap. 54): condiciones
    globales, en UT. Con `latitude` y `longitude`, cada eclipse lunar trae la
    altitud de la Luna en el máximo desde ese lugar. Los eclipses solares no
    incluyen circunstancias locales (requieren elementos besselianos)."""
    solar, lunar = _eclipses(year)
    located = latitude is not None and longitude is not None

    def lunar_item(eclipse: LunarEclipse) -> LunarEclipseItem:
        altitude = moon_altitude(julian_day(eclipse.time), latitude, longitude) if located else None
        return LunarEclipseItem(
            time=eclipse.time,
            kind=str(eclipse.kind),
            gamma=eclipse.gamma,
            penumbral_magnitude=eclipse.penumbral_magnitude,
            umbral_magnitude=eclipse.umbral_magnitude,
            penumbra_start=eclipse.penumbra_start,
            partial_start=eclipse.partial_start,
            total_start=eclipse.total_start,
            total_end=eclipse.total_end,
            partial_end=eclipse.partial_end,
            penumbra_end=eclipse.penumbra_end,
            moon_altitude_deg=altitude,
        )

    return EclipsesResponse(
        year=year,
        solar=[
            SolarEclipseItem(
                time=e.time,
                kind=str(e.kind),
                central=e.central,
                gamma=e.gamma,
                u=e.u,
                magnitude=e.magnitude,
            )
            for e in solar
        ],
        lunar=[lunar_item(e) for e in lunar],
    )
