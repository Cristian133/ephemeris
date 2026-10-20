"""Modelos Pydantic de los endpoints meteorológicos (etapa 3)."""

from typing import Literal

from pydantic import BaseModel


class RainDistribution(BaseModel):
    """Media, mediana y percentiles 10 y 90 (en mm) de la lluvia de un mes o
    de un año, entre los años con dato. `years_with_data` es la cantidad de
    años con que se calculó; todo lo demás es `None` si es 0."""

    years_with_data: int
    mean_mm: float | None
    median_mm: float | None
    p10_mm: float | None
    p90_mm: float | None


class RainMonth(RainDistribution):
    """`month` va de 1 (enero) a 12. `mean_rainy_days` es la media de días
    con lluvia (1 mm o más) del mes."""

    month: int
    mean_rainy_days: float | None


class RainYearTotal(BaseModel):
    """Lluvia total de un año; `None` si a la serie le falta algún mes."""

    year: int
    total_mm: float | None


class RainExtremeYear(BaseModel):
    year: int
    total_mm: float


class RainResponse(BaseModel):
    """Estadísticas de lluvia de la celda de 0.25° que contiene al punto.

    Salen de un reanálisis (ERA5, vía Open-Meteo): es el valor típico de la
    celda, no de una estación; suaviza los extremos y puede subestimar la
    lluvia puntual. Los años van de `first_year` a `last_year`, ambos
    incluidos (por defecto, el período climatológico 1991-2020)."""

    latitude: float
    longitude: float
    grid_latitude: float
    grid_longitude: float
    first_year: int
    last_year: int
    rainy_day_threshold_mm: float
    source: str
    months: list[RainMonth]
    annual: RainDistribution
    yearly_totals: list[RainYearTotal]
    wettest_year: RainExtremeYear | None
    driest_year: RainExtremeYear | None


class _Place(BaseModel):
    """Punto pedido, centro de la celda de 0.25° que se consultó y período
    (años incluidos, ya terminados)."""

    latitude: float
    longitude: float
    grid_latitude: float
    grid_longitude: float
    first_year: int
    last_year: int
    source: str


class CloudDistribution(BaseModel):
    """Nubosidad media (en %) entre los años con dato; `None` si no hay."""

    years_with_data: int
    mean_pct: float | None
    median_pct: float | None
    p10_pct: float | None
    p90_pct: float | None


class CloudMonth(CloudDistribution):
    """`month` va de 1 (enero) a 12. Los días son medias por mes: despejado
    (nubosidad media del día de hasta `clear_max_pct`), cubierto (desde
    `overcast_min_pct`) y parcialmente nublado (el resto)."""

    month: int
    clear_days: float | None
    partly_days: float | None
    overcast_days: float | None


class CloudResponse(_Place):
    """Nubosidad de la celda: media mensual y anual, y días despejados,
    parciales y cubiertos. Es un reanálisis (ERA5), no observación."""

    clear_max_pct: float
    overcast_min_pct: float
    months: list[CloudMonth]
    annual: CloudDistribution


class SunshineDistribution(BaseModel):
    """Horas de sol efectivo entre los años con dato; `None` si no hay."""

    years_with_data: int
    mean_hours: float | None
    median_hours: float | None
    p10_hours: float | None
    p90_hours: float | None


class EstimatedSunshine(BaseModel):
    """Horas de sol estimadas a partir de la radiación (Ångström-Prescott):
    la mejor estimación de lo que mediría un heliógrafo. Las de `mean_hours`
    y compañía son las del modelo del reanálisis, que quedan muy por encima."""

    estimated_mean_hours: float | None
    estimated_median_hours: float | None
    estimated_p10_hours: float | None
    estimated_p90_hours: float | None
    estimated_relative_pct: float | None


class SunshineMonth(SunshineDistribution, EstimatedSunshine):
    """Horas de sol por día del mes. `astronomical_hours` es la duración del
    día (orto a ocaso); `relative_pct` y `estimated_relative_pct`, la media
    (del modelo y estimada) sobre esa duración."""

    month: int
    astronomical_hours: float
    relative_pct: float | None


class SunshineAnnual(SunshineDistribution, EstimatedSunshine):
    """Horas de sol del año (años con los 12 meses completos)."""

    astronomical_hours: float
    relative_pct: float | None


class SunshineResponse(_Place):
    """Horas de sol por mes y por año frente a las astronómicas, de dos
    maneras. `mean_hours` y compañía son la duración de sol efectivo que
    modela el reanálisis (radiación directa útil): quedan ~40-45 % por encima
    de lo medido con heliógrafo. Las `estimated_*` salen de invertir la
    relación de Ångström-Prescott (`angstrom_a`, `angstrom_b`) sobre la
    radiación, y en tres estaciones quedan 10-15 % por encima."""

    angstrom_a: float
    angstrom_b: float
    months: list[SunshineMonth]
    annual: SunshineAnnual


class RadiationDistribution(BaseModel):
    """Radiación global horizontal (kWh/m²) entre los años con dato; `None`
    si no hay. En los meses es por día; en el año, el total."""

    years_with_data: int
    mean_kwh: float | None
    median_kwh: float | None
    p10_kwh: float | None
    p90_kwh: float | None


class RadiationMonth(RadiationDistribution):
    """`month` va de 1 (enero) a 12. `clear_sky_kwh` es la media diaria con
    cielo despejado e `clearness_index` el cociente real / despejado."""

    month: int
    clear_sky_kwh: float
    clearness_index: float | None


class RadiationAnnual(RadiationDistribution):
    """Total anual (años con los 12 meses completos) frente al de cielo despejado."""

    clear_sky_kwh: float
    clearness_index: float | None


class PanelRealSky(BaseModel):
    """Panel fijo en su inclinación anual óptima (mirando al ecuador), en kWh
    por m² de panel y por año. `estimated_kwh_per_m2` aplica a cada mes el
    índice de claridad horizontal: es una estimación, sin separar directa y
    difusa ni descontar pérdidas del sistema."""

    azimuth_deg: float
    tilt_deg: float
    albedo: float
    clear_sky_kwh_per_m2: float
    estimated_kwh_per_m2: float | None


class IrradianceRealResponse(_Place):
    """Radiación solar real de la celda frente a la de cielo despejado
    (Ineichen y Perez, con la altitud y la turbidez de Linke indicadas).

    `elevation_source` dice de dónde salió `elevation_m`: `user` (la pasó el
    cliente), `cell` (la que informa la fuente para la celda) o `default`
    (0 m, porque la fuente no la dio ni se pudo consultar)."""

    elevation_m: float
    elevation_source: Literal["user", "cell", "default"]
    linke_turbidity: float
    months: list[RadiationMonth]
    annual: RadiationAnnual
    panel: PanelRealSky
