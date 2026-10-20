"""Modelos Pydantic de los endpoints de la Luna, el calendario y las mareas
(etapa 2; ver docs/plan_tecnico.md, sección 6)."""

from datetime import date, datetime

from pydantic import BaseModel


class MoonDayResponse(BaseModel):
    """Salida, tránsito y puesta de la Luna en un día solar local, y su
    iluminación al mediodía local.

    Algún día del mes la Luna no sale (o no se pone) dentro del día local:
    el evento es `None`. `always_above` solo se informa si no hay salida ni
    puesta (Luna circumpolar o siempre bajo el horizonte). `phase_key` es
    uno de: new, waxing_crescent, first_quarter, waxing_gibbous, full,
    waning_gibbous, last_quarter, waning_crescent.
    """

    latitude: float
    longitude: float
    date: date
    rise: datetime | None
    transit: datetime | None
    set: datetime | None
    transit_altitude_deg: float | None
    always_above: bool | None
    illuminated_fraction: float
    phase_angle_deg: float
    phase_key: str
    waxing: bool
    age_days: float
    bright_limb_angle_deg: float
    distance_km: float


class MoonPositionSample(BaseModel):
    """Altitud y azimut topocéntricos de la Luna en un instante."""

    time: datetime
    altitude: float
    azimuth: float


class MoonTrajectoryResponse(BaseModel):
    latitude: float
    longitude: float
    date: date
    illuminated_fraction: float
    samples: list[MoonPositionSample]


class MoonPhaseEvent(BaseModel):
    """Fase principal de la Luna. `kind`: new, first_quarter, full o
    last_quarter. `brown_lunation` numera el mes sinódico (la primera Luna
    nueva de 1923 es la lunación 1)."""

    kind: str
    time: datetime
    brown_lunation: int


class MoonPhasesResponse(BaseModel):
    year: int
    phases: list[MoonPhaseEvent]


class EasterDate(BaseModel):
    date: date
    weekday: str


class EasterResponse(BaseModel):
    """Pascua del año: la occidental (calendario gregoriano) y la ortodoxa,
    cuya fecha se calcula en el calendario juliano (`julian_date`, texto
    AAAA-MM-DD) y aquí también se da su equivalente gregoriano."""

    year: int
    western: EasterDate
    orthodox_julian_date: str
    orthodox: EasterDate
    coincide: bool


class TideSample(BaseModel):
    """Marea de equilibrio (m sobre el nivel medio): de la Luna, del Sol y
    la suma."""

    time: datetime
    moon_m: float
    sun_m: float
    total_m: float


class TideExtremeItem(BaseModel):
    time: datetime
    height_m: float
    high: bool


class TideDayResponse(BaseModel):
    """Marea teórica de equilibrio a lo largo de un día solar local. No es
    la altura de la marea real de un puerto: ver `app.solar.tides`.
    `spring_neap_ratio` es el cociente entre la fuerza de marea combinada y
    la lunar sola al mediodía local: ~1.4 en mareas vivas (nueva y llena),
    ~0.5 en mareas muertas (cuadraturas)."""

    latitude: float
    longitude: float
    date: date
    spring_neap_ratio: float
    max_total_m: float
    min_total_m: float
    extremes: list[TideExtremeItem]
    samples: list[TideSample]


class SolarEclipseItem(BaseModel):
    """Eclipse solar global. `kind`: partial, annular, total o hybrid.
    `gamma` (radios terrestres) es positivo si el eje de la sombra pasa al
    norte del centro de la Tierra; `magnitude` solo se informa en los
    parciales. No incluye circunstancias locales."""

    time: datetime
    kind: str
    central: bool
    gamma: float
    u: float
    magnitude: float | None


class LunarEclipseItem(BaseModel):
    """Eclipse lunar. `kind`: penumbral, partial o total. Los contactos son
    `None` si esa fase no ocurre. `moon_altitude_deg` (solo si se indicó
    ubicación) es la altitud de la Luna en el máximo: positiva si el eclipse
    se ve desde ese lugar."""

    time: datetime
    kind: str
    gamma: float
    penumbral_magnitude: float
    umbral_magnitude: float
    penumbra_start: datetime
    partial_start: datetime | None
    total_start: datetime | None
    total_end: datetime | None
    partial_end: datetime | None
    penumbra_end: datetime
    moon_altitude_deg: float | None


class EclipsesResponse(BaseModel):
    year: int
    solar: list[SolarEclipseItem]
    lunar: list[LunarEclipseItem]


class ApsisItem(BaseModel):
    """Perigeo o apogeo de la Luna. `kind`: perigee o apogee."""

    kind: str
    time: datetime
    distance_km: float
    parallax_arcsec: float


class ApsidesResponse(BaseModel):
    year: int
    apsides: list[ApsisItem]
