"""Grilla de caché: las series se piden y guardan por celda, no por punto.

ERA5 tiene una resolución nativa de 0.25°: dos puntos de la misma celda dan
prácticamente la misma serie, así que se consulta el centro de la celda y se
comparte el resultado. Evita llamadas repetidas por coordenadas casi iguales.
"""

import math
from dataclasses import dataclass

CELL_DEGREES = 0.25
_LON_CELLS = round(360 / CELL_DEGREES)


@dataclass(frozen=True)
class Cell:
    """Celda de la grilla, por índice entero (0 es el meridiano/ecuador)."""

    lat_index: int
    lon_index: int

    @property
    def latitude(self) -> float:
        return self.lat_index * CELL_DEGREES

    @property
    def longitude(self) -> float:
        return self.lon_index * CELL_DEGREES


def cell_for(latitude: float, longitude: float) -> Cell:
    """Celda cuyo centro es el más cercano al punto (mitades hacia arriba)."""
    lat_index = math.floor(latitude / CELL_DEGREES + 0.5)
    lon_index = math.floor(longitude / CELL_DEGREES + 0.5)
    # +180 y -180 son el mismo meridiano: se normaliza a [-180, 180).
    lon_index = (lon_index + _LON_CELLS // 2) % _LON_CELLS - _LON_CELLS // 2
    return Cell(lat_index, lon_index)
