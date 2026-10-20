"""Parámetros de consulta compartidos por los routers."""

from datetime import date as date_type
from typing import Annotated

from fastapi import Query

_MIN_SAMPLES = 24
_MAX_SAMPLES = 288

Latitude = Annotated[float, Query(ge=-90, le=90, description="Latitud del observador, en grados")]
Longitude = Annotated[
    float,
    Query(ge=-180, le=180, description="Longitud del observador, en grados (positiva al este)"),
]
DateParam = Annotated[
    date_type,
    Query(
        description=(
            "Fecha del día solar local del observador (YYYY-MM-DD): el día que va de una "
            "medianoche media local a la siguiente, no el día UTC"
        )
    ),
]
NumSamples = Annotated[
    int,
    Query(
        ge=_MIN_SAMPLES,
        le=_MAX_SAMPLES,
        description="Cantidad de instantes a muestrear a lo largo del día (equiespaciados)",
    ),
]

Elevation = Annotated[
    float,
    Query(
        ge=-500,
        le=9000,
        description="Altitud del lugar sobre el nivel del mar, en metros",
    ),
]
LinkeTurbidity = Annotated[
    float,
    Query(
        ge=1,
        le=8,
        description=(
            "Factor de turbidez de Linke (1 = aire limpio y seco; 2-5 típico; "
            "más en ciudades e industria)"
        ),
    ),
]
Albedo = Annotated[
    float,
    Query(ge=0, le=1, description="Reflectividad del suelo (pasto ~0.2, nieve fresca ~0.8)"),
]
