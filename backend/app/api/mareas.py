"""Endpoints de mareas teóricas (etapa 2)."""

from fastapi import APIRouter

from app.api.params import DateParam, Latitude, Longitude
from app.schemas.luna import TideDayResponse, TideExtremeItem, TideSample
from app.solar.events import local_day_start_jd
from app.solar.tides import day_tide_series, spring_neap_ratio, tide_extremes

router = APIRouter()


@router.get("/dia", response_model=TideDayResponse)
def dia(latitude: Latitude, longitude: Longitude, date: DateParam) -> TideDayResponse:
    """Marea teórica de equilibrio (Sol y Luna) a lo largo del día solar
    local: serie cada 10 minutos, pleamares y bajamares de equilibrio y
    ciclo de mareas vivas y muertas. No es la altura de la marea real de
    una costa (ver `app.solar.tides`)."""
    series = day_tide_series(date, latitude, longitude)
    start_jd = local_day_start_jd(date, longitude)
    return TideDayResponse(
        latitude=latitude,
        longitude=longitude,
        date=date,
        spring_neap_ratio=spring_neap_ratio(start_jd + 0.5),
        max_total_m=max(series.total_m),
        min_total_m=min(series.total_m),
        extremes=[
            TideExtremeItem(time=e.time, height_m=e.height_m, high=e.high)
            for e in tide_extremes(start_jd, 1.0, latitude, longitude)
        ],
        samples=[
            TideSample(time=time, moon_m=moon, sun_m=sun, total_m=total)
            for time, moon, sun, total in zip(
                series.times, series.moon_m, series.sun_m, series.total_m, strict=True
            )
        ],
    )
