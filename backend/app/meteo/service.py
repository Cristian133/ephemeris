"""Orquesta cliente y caché: pide a la fuente solo lo que falta."""

from collections.abc import Callable
from datetime import date

from app.meteo.client import OpenMeteoArchiveClient
from app.meteo.grid import Cell, cell_for
from app.meteo.series import DailySeries
from app.meteo.store import MeteoStore

# Primer año del reanálisis ERA5 que expone Open-Meteo.
MIN_YEAR = 1940


class MeteoService:
    def __init__(
        self,
        client: OpenMeteoArchiveClient,
        store: MeteoStore,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._client = client
        self._store = store
        self._today = today

    def daily(
        self, latitude: float, longitude: float, first_year: int, last_year: int
    ) -> DailySeries:
        """Serie diaria de `first_year` a `last_year` (inclusive) en la celda del punto.

        Solo admite años cerrados: el año en curso está incompleto y ERA5
        tiene unos días de demora, así que sus estadísticas serían engañosas
        y no se pueden dejar en un caché que se da por definitivo.
        """
        if first_year > last_year:
            raise ValueError("`first_year` no puede ser posterior a `last_year`")
        if first_year < MIN_YEAR:
            raise ValueError(f"No hay datos anteriores a {MIN_YEAR}")
        if last_year >= self._today().year:
            raise ValueError("Solo hay estadísticas de años ya terminados")
        cell = cell_for(latitude, longitude)
        self._fill(cell, first_year, last_year)
        return self._store.load(cell, first_year, last_year)

    def cell_elevation(self, latitude: float, longitude: float) -> float | None:
        """Altitud (m) de la celda del punto, según la fuente.

        Sale del caché; los datos pedidos antes de que se guardara la
        altitud no la tienen, y se recupera con una consulta mínima (un día).
        `None` si la fuente no la informa.
        """
        cell = cell_for(latitude, longitude)
        cached = self._store.elevation(cell)
        if cached is not None:
            return cached
        probe_day = date(self._today().year - 1, 1, 1)
        elevation = self._client.fetch_daily(
            cell.latitude, cell.longitude, probe_day, probe_day
        ).elevation_m
        if elevation is not None:
            self._store.save_elevation(cell, elevation)
        return elevation

    def _fill(self, cell: Cell, first_year: int, last_year: int) -> None:
        cached = self._store.cached_years(cell)
        # Un pedido por tramo de años contiguos que faltan, no uno por año.
        run: list[int] = []
        for year in [*range(first_year, last_year + 1), None]:
            if year is not None and year not in cached:
                run.append(year)
                continue
            if run:
                years = range(run[0], run[-1] + 1)
                data = self._client.fetch_daily(
                    cell.latitude,
                    cell.longitude,
                    date(years.start, 1, 1),
                    date(years.stop - 1, 12, 31),
                )
                self._store.save_years(cell, years, data.series)
                if data.elevation_m is not None:
                    self._store.save_elevation(cell, data.elevation_m)
                run = []
