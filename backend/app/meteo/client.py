"""Cliente de la API histórica de Open-Meteo (reanálisis ERA5).

Gratuita y sin API key, pero solo para uso no comercial y con límite de
llamadas: por eso se reintenta ante 429 y 5xx con espera creciente, y el
resto del paquete guarda en disco lo que ya pidió. Se pide con
`timezone=auto`, de modo que cada fila es un día local del lugar (mismo
criterio que el parámetro `date` de la API solar).
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import httpx
import numpy as np

from app.meteo.series import DailySeries

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARIABLES = (
    "precipitation_sum",
    "cloud_cover_mean",
    "sunshine_duration",
    "shortwave_radiation_sum",
)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class ArchiveData:
    """Lo que devuelve la fuente: la serie y la altitud (m) del punto que
    resolvió, o `None` si no la informó."""

    series: DailySeries
    elevation_m: float | None


class MeteoSourceError(RuntimeError):
    """La fuente de datos no respondió o devolvió algo inesperado."""


class OpenMeteoArchiveClient:
    def __init__(
        self,
        base_url: str = ARCHIVE_URL,
        http: httpx.Client | None = None,
        max_attempts: int = 3,
        backoff_s: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url
        self._http = http or httpx.Client(timeout=30.0)
        self._max_attempts = max_attempts
        self._backoff_s = backoff_s
        self._sleep = sleep

    def fetch_daily(self, latitude: float, longitude: float, start: date, end: date) -> ArchiveData:
        """Serie diaria de `start` a `end` (inclusive) para el punto dado."""
        if end < start:
            raise ValueError("`end` no puede ser anterior a `start`")
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "auto",
        }
        return _parse(self._get(params))

    def _get(self, params: dict[str, str | float]) -> dict:
        last_error = "sin respuesta"
        for attempt in range(self._max_attempts):
            if attempt:
                self._sleep(self._backoff_s * 2 ** (attempt - 1))
            try:
                response = self._http.get(self._base_url, params=params)
            except httpx.TransportError as error:
                last_error = f"error de red ({error.__class__.__name__})"
                continue
            if response.status_code in _RETRYABLE_STATUS:
                last_error = f"HTTP {response.status_code}{_reason(response)}"
                continue
            if response.status_code != 200:
                raise MeteoSourceError(f"Open-Meteo respondió HTTP {response.status_code}")
            try:
                return response.json()
            except ValueError as error:
                raise MeteoSourceError(
                    "Open-Meteo devolvió una respuesta que no es JSON"
                ) from error
        raise MeteoSourceError(
            f"Open-Meteo no disponible tras {self._max_attempts} intentos: {last_error}"
        )


def _reason(response: httpx.Response) -> str:
    """El motivo que da la fuente (ej. el límite de uso por minuto), si lo hay."""
    try:
        reason = response.json().get("reason")
    except (ValueError, AttributeError):
        return ""
    return f" ({reason})" if isinstance(reason, str) and reason else ""


def _parse(payload: dict) -> ArchiveData:
    daily = payload.get("daily")
    if not isinstance(daily, dict) or "time" not in daily:
        raise MeteoSourceError("Open-Meteo no devolvió la sección `daily`")
    dates = np.array(daily["time"], dtype="datetime64[D]")
    columns = []
    for name in DAILY_VARIABLES:
        values = daily.get(name)
        if values is None or len(values) != len(dates):
            raise MeteoSourceError(f"Open-Meteo no devolvió `{name}` completo")
        # Los días sin dato vienen como null.
        columns.append(np.array([np.nan if v is None else v for v in values], dtype=float))
    elevation = payload.get("elevation")
    return ArchiveData(
        DailySeries(dates, *columns),
        float(elevation) if isinstance(elevation, int | float) else None,
    )
