"""Endpoints de `/meteo` (etapa 3; ver docs/plan_tecnico.md, sección 7)."""

from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.params import Albedo, Elevation, Latitude, LinkeTurbidity, Longitude
from app.config import settings
from app.meteo.aggregate import Distribution
from app.meteo.client import MeteoSourceError, OpenMeteoArchiveClient
from app.meteo.grid import cell_for
from app.meteo.radiation import estimate_panel_real_sky, radiation_statistics
from app.meteo.rain import RAINY_DAY_MM, rain_statistics
from app.meteo.series import DailySeries
from app.meteo.service import MIN_YEAR, MeteoService
from app.meteo.sky import (
    ANGSTROM_A,
    ANGSTROM_B,
    CLEAR_MAX_PCT,
    OVERCAST_MIN_PCT,
    REFERENCE_YEAR,
    astronomical_daylight_hours,
    cloud_statistics,
    estimated_sunshine_statistics,
    sunshine_statistics,
)
from app.meteo.store import MeteoStore
from app.schemas.meteo import (
    CloudDistribution,
    CloudMonth,
    CloudResponse,
    IrradianceRealResponse,
    PanelRealSky,
    RadiationAnnual,
    RadiationMonth,
    RainDistribution,
    RainExtremeYear,
    RainMonth,
    RainResponse,
    RainYearTotal,
    SunshineAnnual,
    SunshineMonth,
    SunshineResponse,
)
from app.solar.insolation import clear_sky_daily_ghi_kwh, extraterrestrial_daily_kwh
from app.solar.irradiance import DEFAULT_LINKE_TURBIDITY
from app.solar.panel import DEFAULT_ALBEDO, optimal_panel_orientation

router = APIRouter()

SOURCE = "ERA5 (reanálisis) vía Open-Meteo"

FirstYear = Annotated[
    int, Query(ge=MIN_YEAR, le=2100, description="Primer año del período (incluido)")
]
LastYear = Annotated[
    int,
    Query(ge=MIN_YEAR, le=2100, description="Último año del período (incluido); ya terminado"),
]


@lru_cache(maxsize=1)
def get_meteo_service() -> MeteoService:
    return MeteoService(OpenMeteoArchiveClient(), MeteoStore(settings.meteo_db_path))


def _distribution(d: Distribution, unit: str) -> dict:
    """Campos de resumen con la unidad en el nombre (`mean_mm`, `mean_pct`...)."""
    return {
        "years_with_data": d.count,
        f"mean_{unit}": d.mean,
        f"median_{unit}": d.median,
        f"p10_{unit}": d.p10,
        f"p90_{unit}": d.p90,
    }


def _load(
    service: MeteoService, latitude: float, longitude: float, first_year: int, last_year: int
) -> DailySeries:
    """Serie diaria del período, con los errores del servicio como HTTP."""
    try:
        return service.daily(latitude, longitude, first_year, last_year)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except MeteoSourceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


def _place(latitude: float, longitude: float, first_year: int, last_year: int) -> dict:
    cell = cell_for(latitude, longitude)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "grid_latitude": cell.latitude,
        "grid_longitude": cell.longitude,
        "first_year": first_year,
        "last_year": last_year,
        "source": SOURCE,
    }


@router.get("/lluvia", response_model=RainResponse)
def lluvia(
    latitude: Latitude,
    longitude: Longitude,
    service: Annotated[MeteoService, Depends(get_meteo_service)],
    first_year: FirstYear = 1991,
    last_year: LastYear = 2020,
) -> RainResponse:
    """Lluvia mensual y anual del período: media, mediana, percentiles 10 y
    90, días de lluvia, y los años más seco y más húmedo.

    La primera consulta de un lugar baja la serie de la fuente (puede tardar
    unos segundos); las siguientes salen del caché local."""
    series = _load(service, latitude, longitude, first_year, last_year)
    stats = rain_statistics(series)
    totals_by_year = dict(zip(stats.years, stats.yearly_totals, strict=True))
    return RainResponse(
        **_place(latitude, longitude, first_year, last_year),
        rainy_day_threshold_mm=RAINY_DAY_MM,
        months=[
            RainMonth(month=m + 1, mean_rainy_days=stats.rainy_days[m], **_distribution(d, "mm"))
            for m, d in enumerate(stats.monthly)
        ],
        annual=RainDistribution(**_distribution(stats.annual, "mm")),
        yearly_totals=[
            RainYearTotal(year=y, total_mm=totals_by_year.get(y))
            for y in range(first_year, last_year + 1)
        ],
        wettest_year=(
            RainExtremeYear(year=stats.wettest_year.year, total_mm=stats.wettest_year.total_mm)
            if stats.wettest_year
            else None
        ),
        driest_year=(
            RainExtremeYear(year=stats.driest_year.year, total_mm=stats.driest_year.total_mm)
            if stats.driest_year
            else None
        ),
    )


@router.get("/nubosidad", response_model=CloudResponse)
def nubosidad(
    latitude: Latitude,
    longitude: Longitude,
    service: Annotated[MeteoService, Depends(get_meteo_service)],
    first_year: FirstYear = 1991,
    last_year: LastYear = 2020,
) -> CloudResponse:
    """Nubosidad media mensual y anual del período, y días despejados,
    parcialmente nublados y cubiertos de cada mes."""
    stats = cloud_statistics(_load(service, latitude, longitude, first_year, last_year))
    return CloudResponse(
        **_place(latitude, longitude, first_year, last_year),
        clear_max_pct=CLEAR_MAX_PCT,
        overcast_min_pct=OVERCAST_MIN_PCT,
        months=[
            CloudMonth(
                month=m + 1,
                clear_days=month.clear_days,
                partly_days=month.partly_days,
                overcast_days=month.overcast_days,
                **_distribution(month.cover, "pct"),
            )
            for m, month in enumerate(stats.monthly)
        ],
        annual=CloudDistribution(**_distribution(stats.annual, "pct")),
    )


def _estimated(d: Distribution, relative_pct: float | None) -> dict:
    return {
        "estimated_mean_hours": d.mean,
        "estimated_median_hours": d.median,
        "estimated_p10_hours": d.p10,
        "estimated_p90_hours": d.p90,
        "estimated_relative_pct": relative_pct,
    }


@router.get("/horas-sol", response_model=SunshineResponse)
def horas_sol(
    latitude: Latitude,
    longitude: Longitude,
    service: Annotated[MeteoService, Depends(get_meteo_service)],
    first_year: FirstYear = 1991,
    last_year: LastYear = 2020,
) -> SunshineResponse:
    """Horas de sol por mes y por año frente a la duración astronómica del
    día, con la insolación relativa (cuánto del día con Sol sobre el
    horizonte llega a brillar).

    Trae dos versiones: la del modelo del reanálisis (`mean_hours`...), que
    sobreestima mucho, y la estimada desde la radiación con Ångström-Prescott
    (`estimated_*`), que se acerca bastante más a lo medido en estaciones."""
    series = _load(service, latitude, longitude, first_year, last_year)
    place = _place(latitude, longitude, first_year, last_year)
    # La duración del día se calcula para el centro de la celda, igual que los datos.
    grid = (place["grid_latitude"], place["grid_longitude"])
    daylight = astronomical_daylight_hours(*grid)
    model = sunshine_statistics(series, daylight)
    estimate = estimated_sunshine_statistics(
        series, extraterrestrial_daily_kwh(REFERENCE_YEAR, *grid), daylight
    )
    return SunshineResponse(
        **place,
        angstrom_a=ANGSTROM_A,
        angstrom_b=ANGSTROM_B,
        months=[
            SunshineMonth(
                month=m + 1,
                astronomical_hours=month.astronomical_hours_per_day,
                relative_pct=month.relative_pct,
                **_distribution(month.hours_per_day, "hours"),
                **_estimated(est.hours_per_day, est.relative_pct),
            )
            for m, (month, est) in enumerate(zip(model.monthly, estimate.monthly, strict=True))
        ],
        annual=SunshineAnnual(
            astronomical_hours=model.astronomical_annual_hours,
            relative_pct=model.annual_relative_pct,
            **_distribution(model.annual_hours, "hours"),
            **_estimated(estimate.annual_hours, estimate.annual_relative_pct),
        ),
    )


_MIN_ELEVATION_M, _MAX_ELEVATION_M = -500.0, 9000.0


def _resolve_elevation(
    service: MeteoService, latitude: float, longitude: float, requested: float | None
) -> tuple[float, Literal["user", "cell", "default"]]:
    """Altitud a usar: la pedida, la de la celda o, sin ninguna, el nivel del mar.

    Los datos ya están en el caché cuando se llega acá, así que si la fuente
    no responde solo para consultar la altitud no se rechaza el pedido: se usa
    0 m y se avisa en la respuesta."""
    if requested is not None:
        return requested, "user"
    try:
        cell_elevation = service.cell_elevation(latitude, longitude)
    except MeteoSourceError:
        cell_elevation = None
    if cell_elevation is None:
        return 0.0, "default"
    return min(max(cell_elevation, _MIN_ELEVATION_M), _MAX_ELEVATION_M), "cell"


@router.get("/irradiancia-real", response_model=IrradianceRealResponse)
def irradiancia_real(
    latitude: Latitude,
    longitude: Longitude,
    service: Annotated[MeteoService, Depends(get_meteo_service)],
    first_year: FirstYear = 1991,
    last_year: LastYear = 2020,
    elevation_m: Elevation | None = None,
    linke_turbidity: LinkeTurbidity = DEFAULT_LINKE_TURBIDITY,
    albedo: Albedo = DEFAULT_ALBEDO,
) -> IrradianceRealResponse:
    """Radiación solar global horizontal real (reanálisis) por mes y por año
    frente a la de cielo despejado, con el índice de claridad, y la energía
    anual estimada de un panel fijo óptimo con el cielo real.

    El cielo despejado se calcula para el centro de la celda, igual que los
    datos. Si no se pasa `elevation_m`, usa la altitud que informa la fuente
    para la celda (0 m si no se pudo obtener); la respuesta indica cuál usó."""
    series = _load(service, latitude, longitude, first_year, last_year)
    place = _place(latitude, longitude, first_year, last_year)
    grid = (place["grid_latitude"], place["grid_longitude"])

    elevation_m, elevation_source = _resolve_elevation(service, latitude, longitude, elevation_m)
    clear_daily = clear_sky_daily_ghi_kwh(REFERENCE_YEAR, *grid, elevation_m, linke_turbidity)
    stats = radiation_statistics(series, clear_daily)

    orientation = optimal_panel_orientation(
        REFERENCE_YEAR, *grid, elevation_m, linke_turbidity, albedo
    )
    return IrradianceRealResponse(
        **place,
        elevation_m=elevation_m,
        elevation_source=elevation_source,
        linke_turbidity=linke_turbidity,
        months=[
            RadiationMonth(
                month=m + 1,
                clear_sky_kwh=month.clear_sky_kwh_per_day,
                clearness_index=month.clearness_index,
                **_distribution(month.real, "kwh"),
            )
            for m, month in enumerate(stats.monthly)
        ],
        annual=RadiationAnnual(
            clear_sky_kwh=stats.clear_sky_annual_kwh,
            clearness_index=stats.annual_clearness_index,
            **_distribution(stats.annual_real, "kwh"),
        ),
        panel=PanelRealSky(
            azimuth_deg=orientation.azimuth_deg,
            tilt_deg=orientation.annual_tilt_deg,
            albedo=albedo,
            clear_sky_kwh_per_m2=sum(orientation.monthly_kwh_per_m2),
            estimated_kwh_per_m2=estimate_panel_real_sky(orientation.monthly_kwh_per_m2, stats),
        ),
    )
