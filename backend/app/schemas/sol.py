"""Modelos Pydantic de request/response del endpoint `/sol` (ver
docs/plan_tecnico.md, sección 5)."""

from datetime import date, datetime

from pydantic import BaseModel


class DailySun(BaseModel):
    """Eventos solares de un día dentro de la evolución anual.

    `transit` siempre está presente. `sunrise`/`sunset` son `None` en un
    día polar (sol de medianoche o noche polar) — `always_above` distingue
    cuál de los dos es, y en ese caso `day_length_hours` también es `None`.
    """

    date: date
    transit: datetime
    sunrise: datetime | None
    sunset: datetime | None
    day_length_hours: float | None
    always_above: bool | None


class AnnualSunResponse(BaseModel):
    """Evolución anual de las horas de sol para una ubicación."""

    latitude: float
    longitude: float
    year: int
    days: list[DailySun]


class DailySunResponse(DailySun):
    """Horas de sol de un único día (punto 1) — mismos campos que
    `DailySun`, con la ubicación consultada."""

    latitude: float
    longitude: float


class SunPosition(BaseModel):
    """Posición del Sol (altitud/azimut) en un instante dado.

    `altitude` es la altitud verdadera (geométrica); `apparent_altitude`
    es la que realmente se vería (corrección por refracción atmosférica,
    más notoria cerca del horizonte)."""

    time: datetime
    altitude: float
    apparent_altitude: float
    azimuth: float


class TrajectoryResponse(BaseModel):
    """Trayectoria del Sol a lo largo de un día, para una ubicación —
    base del gráfico polar del punto 3."""

    latitude: float
    longitude: float
    date: date
    pressure_mbar: float
    temperature_c: float
    samples: list[SunPosition]


class SolarNoonResponse(BaseModel):
    """Mediodía solar e inclinación del Sol en ese instante (punto 4).

    `altitude_deg` es la altitud verdadera máxima del día;
    `apparent_altitude_deg` es la que realmente se vería (corrección por
    refracción). `azimuth_deg` es 0° (Norte) o 180° (Sur) salvo en el caso
    límite del Sol en el cenit. `pressure_mbar` y `temperature_c` son las
    condiciones atmosféricas con que se calculó la refracción."""

    latitude: float
    longitude: float
    date: date
    pressure_mbar: float
    temperature_c: float
    transit: datetime
    altitude_deg: float
    apparent_altitude_deg: float
    azimuth_deg: float


class IrradianceSample(BaseModel):
    """Irradiancia solar (cielo despejado) sobre una superficie horizontal
    en un instante dado: `power_w_per_m2` es la global (directa + difusa)."""

    time: datetime
    power_w_per_m2: float
    direct_w_per_m2: float
    diffuse_w_per_m2: float


class IrradianceResponse(BaseModel):
    """Irradiancia solar a lo largo de un día y la energía total recibida
    por m² en el día, en cielo despejado (punto 5), con su desglose en
    componente directa y difusa. `elevation_m` y `linke_turbidity` son los
    parámetros del modelo con que se calculó."""

    latitude: float
    longitude: float
    date: date
    elevation_m: float
    linke_turbidity: float
    energy_wh_per_m2: float
    direct_energy_wh_per_m2: float
    diffuse_energy_wh_per_m2: float
    samples: list[IrradianceSample]


class AltitudeCrossing(BaseModel):
    """Instantes en que el Sol sube (`rise`) y baja (`set`) por una
    altitud dada. Ambos son `None` si ese día no la cruza; `always_above`
    indica entonces si queda todo el día por encima o por debajo."""

    altitude_deg: float
    rise: datetime | None
    set: datetime | None
    always_above: bool | None


class TwilightResponse(BaseModel):
    """Cruces del Sol por las altitudes que delimitan los crepúsculos y las
    horas azul y dorada, de la más baja a la más alta: astronómico (-18°),
    náutico (-12°), civil (-6°), límite de hora azul (-4°), horizonte
    (orto/ocaso, -0.83°) y límite de hora dorada (+6°).

    Mañana: la hora azul va del cruce civil al de -4°, la dorada del de -4°
    al de +6°. Tarde: al revés (dorada de +6° a -4°, azul de -4° a -6°).
    """

    latitude: float
    longitude: float
    date: date
    astronomical: AltitudeCrossing
    nautical: AltitudeCrossing
    civil: AltitudeCrossing
    blue_hour_limit: AltitudeCrossing
    horizon: AltitudeCrossing
    golden_hour_limit: AltitudeCrossing


class SeasonsResponse(BaseModel):
    """Equinoccios y solsticios de un año (UT). Qué estación inicia cada
    uno depende del hemisferio: el equinoccio de marzo es el otoño austral
    y la primavera boreal."""

    year: int
    march_equinox: datetime
    june_solstice: datetime
    september_equinox: datetime
    december_solstice: datetime


class TiltEnergy(BaseModel):
    """Energía anual recibida por m² de panel para una inclinación."""

    tilt_deg: float
    annual_kwh_per_m2: float


class PanelResponse(BaseModel):
    """Orientación óptima de un panel solar fijo (cielo despejado, con
    componentes directa, difusa y reflejada por el suelo). `azimuth_deg` es
    hacia dónde mira (0°=Norte, 180°=Sur); las inclinaciones se miden desde
    la horizontal. `elevation_m`, `linke_turbidity` y `albedo` son los
    parámetros del modelo con que se calculó."""

    latitude: float
    longitude: float
    year: int
    elevation_m: float
    linke_turbidity: float
    albedo: float
    azimuth_deg: float
    annual_tilt_deg: float
    winter_tilt_deg: float
    summer_tilt_deg: float
    annual_kwh_per_m2: float
    horizontal_kwh_per_m2: float
    curve: list[TiltEnergy]
