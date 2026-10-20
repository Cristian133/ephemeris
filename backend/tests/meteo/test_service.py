from datetime import date

import httpx
import numpy as np
import pytest

from app.meteo.client import OpenMeteoArchiveClient
from app.meteo.grid import cell_for
from app.meteo.service import MeteoService
from app.meteo.store import MeteoStore


class FakeSource:
    """Genera una serie determinista y registra cada pedido."""

    def __init__(self) -> None:
        self.requests: list[tuple[float, float, str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        p = request.url.params
        self.requests.append(
            (float(p["latitude"]), float(p["longitude"]), p["start_date"], p["end_date"])
        )
        days = np.arange(
            np.datetime64(p["start_date"]),
            np.datetime64(p["end_date"]) + np.timedelta64(1, "D"),
            dtype="datetime64[D]",
        )
        ones = [1.0] * len(days)
        return httpx.Response(
            200,
            json={
                "elevation": 650.0,
                "daily": {
                    "time": [str(d) for d in days],
                    "precipitation_sum": ones,
                    "cloud_cover_mean": ones,
                    "sunshine_duration": ones,
                    "shortwave_radiation_sum": ones,
                },
            },
        )


def _service(source: FakeSource, today: date = date(2026, 6, 1)) -> tuple[MeteoService, MeteoStore]:
    client = OpenMeteoArchiveClient(
        base_url="https://example.test/archive",
        http=httpx.Client(transport=httpx.MockTransport(source)),
    )
    store = MeteoStore(":memory:")
    return MeteoService(client, store, today=lambda: today), store


def test_requests_the_cell_center_and_returns_the_series() -> None:
    source = FakeSource()
    service, _ = _service(source)
    series = service.daily(-34.6037, -58.3816, 2020, 2020)
    assert source.requests == [(-34.5, -58.5, "2020-01-01", "2020-12-31")]
    assert len(series) == 366


def test_second_call_is_served_from_the_cache() -> None:
    source = FakeSource()
    service, _ = _service(source)
    service.daily(-34.60, -58.38, 2019, 2020)
    service.daily(-34.55, -58.45, 2019, 2020)  # otro punto, misma celda
    assert len(source.requests) == 1


def test_only_the_missing_year_runs_are_requested() -> None:
    source = FakeSource()
    service, store = _service(source)
    service.daily(-34.6, -58.4, 2019, 2019)
    service.daily(-34.6, -58.4, 2021, 2021)
    source.requests.clear()
    series = service.daily(-34.6, -58.4, 2018, 2022)
    assert [(r[2], r[3]) for r in source.requests] == [
        ("2018-01-01", "2018-12-31"),
        ("2020-01-01", "2020-12-31"),
        ("2022-01-01", "2022-12-31"),
    ]
    assert len(series) == sum(366 if y % 4 == 0 else 365 for y in range(2018, 2023))
    assert store.cached_years(cell_for(-34.6, -58.4)) == set(range(2018, 2023))


def test_cache_persists_across_instances_on_disk(tmp_path) -> None:
    path = tmp_path / "sub" / "meteo.sqlite"
    first_source = FakeSource()
    client = OpenMeteoArchiveClient(
        base_url="https://example.test/archive",
        http=httpx.Client(transport=httpx.MockTransport(first_source)),
    )
    MeteoService(client, MeteoStore(path), today=lambda: date(2026, 6, 1)).daily(0, 0, 2020, 2020)

    second_source = FakeSource()
    other = OpenMeteoArchiveClient(
        base_url="https://example.test/archive",
        http=httpx.Client(transport=httpx.MockTransport(second_source)),
    )
    series = MeteoService(other, MeteoStore(path), today=lambda: date(2026, 6, 1)).daily(
        0, 0, 2020, 2020
    )
    assert second_source.requests == []
    assert len(series) == 366


def test_nan_values_survive_the_round_trip() -> None:
    store = MeteoStore(":memory:")
    cell = cell_for(0, 0)
    from app.meteo.series import DailySeries

    dates = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[D]")
    nan = np.array([np.nan, 1.0])
    store.save_years(cell, range(2020, 2021), DailySeries(dates, nan, nan, nan, nan))
    loaded = store.load(cell, 2020, 2020)
    assert np.isnan(loaded.precipitation_mm[0])
    assert loaded.precipitation_mm[1] == 1.0


@pytest.mark.parametrize(
    ("first", "last"),
    [(2021, 2020), (1939, 1940), (2020, 2026), (2020, 2027)],
)
def test_rejects_years_that_are_invalid_or_not_closed(first: int, last: int) -> None:
    service, _ = _service(FakeSource(), today=date(2026, 6, 1))
    with pytest.raises(ValueError):
        service.daily(0, 0, first, last)


def test_elevation_is_saved_with_the_first_download_and_needs_no_extra_request() -> None:
    source = FakeSource()
    service, store = _service(source)
    service.daily(40.4, -3.7, 2020, 2020)
    assert store.elevation(cell_for(40.4, -3.7)) == 650.0
    source.requests.clear()
    assert service.cell_elevation(40.4, -3.7) == 650.0
    assert source.requests == []


def test_elevation_of_a_cell_cached_before_it_was_stored_costs_one_day_request() -> None:
    source = FakeSource()
    service, store = _service(source)
    cell = cell_for(40.4, -3.7)
    service.daily(40.4, -3.7, 2020, 2020)
    with store._lock, store._db:  # simula un caché anterior a que se guardara la altitud
        store._db.execute("DELETE FROM cells")
    source.requests.clear()

    assert service.cell_elevation(40.4, -3.7) == 650.0
    assert source.requests == [(cell.latitude, cell.longitude, "2025-01-01", "2025-01-01")]
    source.requests.clear()
    assert service.cell_elevation(40.4, -3.7) == 650.0  # ahora sí queda guardada
    assert source.requests == []


def test_elevation_survives_a_new_store_on_the_same_file(tmp_path) -> None:
    path = tmp_path / "meteo.sqlite"
    cell = cell_for(0, 0)
    MeteoStore(path).save_elevation(cell, 123.5)
    assert MeteoStore(path).elevation(cell) == 123.5
    assert MeteoStore(path).elevation(cell_for(10, 10)) is None
