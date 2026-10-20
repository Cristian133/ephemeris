"""Serie diaria de variables meteorológicas de un lugar."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DailySeries:
    """Un valor por día local del lugar; `NaN` donde la fuente no tiene dato.

    - `precipitation_mm`: precipitación total del día.
    - `cloud_cover_pct`: cobertura nubosa media del día (0 a 100).
    - `sunshine_s`: segundos de sol efectivo (con radiación directa útil).
    - `radiation_mj_m2`: radiación de onda corta acumulada del día, en MJ/m².
    """

    dates: np.ndarray  # datetime64[D], ascendente y sin repetidos
    precipitation_mm: np.ndarray
    cloud_cover_pct: np.ndarray
    sunshine_s: np.ndarray
    radiation_mj_m2: np.ndarray

    def __post_init__(self) -> None:
        size = len(self.dates)
        for values in (
            self.precipitation_mm,
            self.cloud_cover_pct,
            self.sunshine_s,
            self.radiation_mj_m2,
        ):
            if len(values) != size:
                raise ValueError("Todas las variables deben tener un valor por fecha")

    def __len__(self) -> int:
        return len(self.dates)


def empty_series() -> DailySeries:
    nothing = np.array([], dtype=float)
    return DailySeries(np.array([], dtype="datetime64[D]"), nothing, nothing, nothing, nothing)
