"""Endpoints de calendario (etapa 2)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.luna import EasterDate, EasterResponse
from app.solar.calendars import easter, julian_to_gregorian, weekday_name

router = APIRouter()


@router.get("/pascua", response_model=EasterResponse)
def pascua(
    year: Annotated[int, Query(ge=1583, le=9999, description="Año (calendario gregoriano)")],
) -> EasterResponse:
    """Domingo de Pascua del año, occidental (gregoriana) y ortodoxa
    (calculada en el calendario juliano, con su equivalente gregoriano).
    Meeus cap. 8."""
    western_y, western_m, western_d = easter(year, "gregorian")
    j_y, j_m, j_d = easter(year, "julian")
    o_y, o_m, o_d = julian_to_gregorian(j_y, j_m, j_d)
    western = date(western_y, western_m, western_d)
    orthodox = date(o_y, o_m, o_d)
    return EasterResponse(
        year=year,
        western=EasterDate(date=western, weekday=weekday_name(western_y, western_m, western_d)),
        orthodox_julian_date=f"{j_y:04d}-{j_m:02d}-{j_d:02d}",
        orthodox=EasterDate(date=orthodox, weekday=weekday_name(o_y, o_m, o_d)),
        coincide=western == orthodox,
    )
