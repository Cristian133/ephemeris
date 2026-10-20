"""Caché persistente de series diarias, en SQLite (biblioteca estándar).

Es de uso personal, así que un archivo alcanza: sin servidor ni servicios
extra en Docker Compose. Se guarda por celda de la grilla y se marca qué
años están completos; solo se guardan años ya cerrados, que no cambian.
"""

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.meteo.grid import Cell
from app.meteo.series import DailySeries, empty_series

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily (
    lat_index INTEGER NOT NULL,
    lon_index INTEGER NOT NULL,
    date TEXT NOT NULL,
    precipitation_mm REAL,
    cloud_cover_pct REAL,
    sunshine_s REAL,
    radiation_mj_m2 REAL,
    PRIMARY KEY (lat_index, lon_index, date)
);
CREATE TABLE IF NOT EXISTS cells (
    lat_index INTEGER NOT NULL,
    lon_index INTEGER NOT NULL,
    elevation_m REAL NOT NULL,
    PRIMARY KEY (lat_index, lon_index)
);
CREATE TABLE IF NOT EXISTS cached_years (
    lat_index INTEGER NOT NULL,
    lon_index INTEGER NOT NULL,
    year INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (lat_index, lon_index, year)
);
"""


class MeteoStore:
    def __init__(self, path: str | Path) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # FastAPI atiende los endpoints síncronos en un pool de hilos.
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(_SCHEMA)

    def elevation(self, cell: Cell) -> float | None:
        """Altitud (m) de la celda, o `None` si todavía no se guardó."""
        with self._lock:
            row = self._db.execute(
                "SELECT elevation_m FROM cells WHERE lat_index = ? AND lon_index = ?",
                (cell.lat_index, cell.lon_index),
            ).fetchone()
        return None if row is None else float(row[0])

    def save_elevation(self, cell: Cell, elevation_m: float) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO cells VALUES (?, ?, ?)",
                (cell.lat_index, cell.lon_index, elevation_m),
            )

    def cached_years(self, cell: Cell) -> set[int]:
        with self._lock:
            rows = self._db.execute(
                "SELECT year FROM cached_years WHERE lat_index = ? AND lon_index = ?",
                (cell.lat_index, cell.lon_index),
            ).fetchall()
        return {year for (year,) in rows}

    def save_years(self, cell: Cell, years: range, series: DailySeries) -> None:
        """Guarda `series` y marca `years` como completos, todo o nada.

        Las fechas fuera de `years` se ignoran: la fuente puede devolver de más.
        """
        rows = []
        for i, day in enumerate(series.dates.astype("datetime64[D]").astype(object)):
            if day.year not in years:
                continue
            rows.append(
                (
                    cell.lat_index,
                    cell.lon_index,
                    day.isoformat(),
                    *(
                        None if np.isnan(v) else float(v)
                        for v in (
                            series.precipitation_mm[i],
                            series.cloud_cover_pct[i],
                            series.sunshine_s[i],
                            series.radiation_mj_m2[i],
                        )
                    ),
                )
            )
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with self._lock, self._db:
            self._db.executemany("INSERT OR REPLACE INTO daily VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
            self._db.executemany(
                "INSERT OR REPLACE INTO cached_years VALUES (?, ?, ?, ?)",
                [(cell.lat_index, cell.lon_index, year, now) for year in years],
            )

    def load(self, cell: Cell, first_year: int, last_year: int) -> DailySeries:
        """Serie diaria de los años pedidos (solo los que estén en el caché)."""
        with self._lock:
            rows = self._db.execute(
                "SELECT date, precipitation_mm, cloud_cover_pct, sunshine_s, radiation_mj_m2 "
                "FROM daily WHERE lat_index = ? AND lon_index = ? AND date BETWEEN ? AND ? "
                "ORDER BY date",
                (
                    cell.lat_index,
                    cell.lon_index,
                    f"{first_year:04d}-01-01",
                    f"{last_year:04d}-12-31",
                ),
            ).fetchall()
        if not rows:
            return empty_series()
        dates = np.array([row[0] for row in rows], dtype="datetime64[D]")
        columns = [
            np.array([np.nan if row[i] is None else row[i] for row in rows], dtype=float)
            for i in range(1, 5)
        ]
        return DailySeries(dates, *columns)
