"""Crepúsculos, hora azul y hora dorada.

No hace falta un cálculo nuevo: todos son instantes en que el Sol cruza una
altitud dada, que `app.solar.events.sunrise_sunset` ya resuelve para
cualquier `altitude_deg`. Este módulo solo fija qué altitud corresponde a
cada fenómeno.

Las altitudes de los crepúsculos son las convenciones astronómicas
estándar (centro del Sol bajo el horizonte): civil -6°, náutico -12°,
astronómico -18°. La hora dorada y la azul no tienen una definición
oficial; se usan las más extendidas en fotografía: dorada entre -4° y
+6°, azul entre -6° y -4°.
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.solar.events import STANDARD_ALTITUDE_SUN, sunrise_sunset

CIVIL_ALTITUDE = -6.0
NAUTICAL_ALTITUDE = -12.0
ASTRONOMICAL_ALTITUDE = -18.0
BLUE_HOUR_LIMIT_ALTITUDE = -4.0
GOLDEN_HOUR_LIMIT_ALTITUDE = 6.0


@dataclass(frozen=True)
class AltitudeCrossing:
    """Instantes (UT) en que el Sol sube y baja por `altitude_deg` en el
    día. `rise`/`set` son `None` si ese día no la cruza; `always_above`
    dice entonces si queda todo el día por encima (`True`) o por debajo
    (`False`) de esa altitud."""

    altitude_deg: float
    rise: datetime | None
    set: datetime | None
    always_above: bool | None


@dataclass(frozen=True)
class Twilight:
    """Cruces del Sol por las altitudes que delimitan cada fase del
    crepúsculo, de la más baja a la más alta."""

    astronomical: AltitudeCrossing
    nautical: AltitudeCrossing
    civil: AltitudeCrossing
    blue_hour_limit: AltitudeCrossing
    horizon: AltitudeCrossing
    golden_hour_limit: AltitudeCrossing


def altitude_crossing(
    day: date, latitude_deg: float, longitude_deg: float, altitude_deg: float
) -> AltitudeCrossing:
    result = sunrise_sunset(day, latitude_deg, longitude_deg, altitude_deg)
    return AltitudeCrossing(
        altitude_deg=altitude_deg,
        rise=result.sunrise,
        set=result.sunset,
        always_above=result.always_above,
    )


def twilight(day: date, latitude_deg: float, longitude_deg: float) -> Twilight:
    """Crepúsculos y límites de hora azul/dorada para la fecha y ubicación."""

    def crossing(altitude_deg: float) -> AltitudeCrossing:
        return altitude_crossing(day, latitude_deg, longitude_deg, altitude_deg)

    return Twilight(
        astronomical=crossing(ASTRONOMICAL_ALTITUDE),
        nautical=crossing(NAUTICAL_ALTITUDE),
        civil=crossing(CIVIL_ALTITUDE),
        blue_hour_limit=crossing(BLUE_HOUR_LIMIT_ALTITUDE),
        horizon=crossing(STANDARD_ALTITUDE_SUN),
        golden_hour_limit=crossing(GOLDEN_HOUR_LIMIT_ALTITUDE),
    )
