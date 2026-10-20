from datetime import date

import httpx
import numpy as np
import pytest

from app.meteo.client import MeteoSourceError, OpenMeteoArchiveClient

PAYLOAD = {
    "elevation": 20.0,
    "daily": {
        "time": ["2020-01-01", "2020-01-02", "2020-01-03"],
        "precipitation_sum": [0.0, 12.5, None],
        "cloud_cover_mean": [10, 80, 95],
        "sunshine_duration": [40000.0, 3600.0, None],
        "shortwave_radiation_sum": [25.1, 8.0, 5.5],
    },
}


def _client(handler, sleeps: list[float] | None = None) -> OpenMeteoArchiveClient:
    return OpenMeteoArchiveClient(
        base_url="https://example.test/archive",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        backoff_s=1.0,
        sleep=(sleeps if sleeps is not None else []).append,
    )


def test_parses_the_series_and_turns_nulls_into_nan() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=PAYLOAD)

    data = _client(handler).fetch_daily(-34.5, -58.5, date(2020, 1, 1), date(2020, 1, 3))
    series = data.series
    assert list(series.dates) == list(np.array(PAYLOAD["daily"]["time"], dtype="datetime64[D]"))
    assert series.precipitation_mm[1] == 12.5
    assert np.isnan(series.precipitation_mm[2])
    assert np.isnan(series.sunshine_s[2])
    assert series.cloud_cover_pct[2] == 95


def test_sends_local_day_and_the_requested_range() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        return httpx.Response(200, json=PAYLOAD)

    _client(handler).fetch_daily(-34.5, -58.5, date(2020, 1, 1), date(2020, 1, 3))
    assert seen["timezone"] == "auto"
    assert seen["start_date"] == "2020-01-01"
    assert seen["end_date"] == "2020-01-03"
    assert seen["latitude"] == "-34.5"
    assert "precipitation_sum" in seen["daily"]


def test_retries_with_growing_backoff_then_succeeds() -> None:
    answers = iter([429, 503, 200])
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(answers)
        return httpx.Response(status, json=PAYLOAD if status == 200 else {})

    _client(handler, sleeps).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 3))
    assert sleeps == [1.0, 2.0]


def test_gives_up_after_the_last_attempt() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(MeteoSourceError, match="3 intentos"):
        _client(handler).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 3))


def test_does_not_retry_client_errors() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"reason": "mal"})

    with pytest.raises(MeteoSourceError, match="400"):
        _client(handler).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 3))
    assert calls == 1


def test_rejects_a_response_missing_a_variable() -> None:
    broken = {"daily": {"time": ["2020-01-01"], "precipitation_sum": [1.0]}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=broken)

    with pytest.raises(MeteoSourceError, match="cloud_cover_mean"):
        _client(handler).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 1))


def test_rejects_an_inverted_range() -> None:
    with pytest.raises(ValueError):
        _client(lambda request: httpx.Response(200)).fetch_daily(
            0, 0, date(2020, 1, 2), date(2020, 1, 1)
        )


def test_returns_the_elevation_the_source_resolved() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=PAYLOAD)

    data = _client(handler).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 3))
    assert data.elevation_m == 20.0


def test_elevation_is_none_when_the_source_does_not_report_it() -> None:
    without = {k: v for k, v in PAYLOAD.items() if k != "elevation"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=without)

    assert (
        _client(handler).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 3)).elevation_m is None
    )


def test_the_final_error_carries_the_reason_the_source_gave() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"error": True, "reason": "Minutely API request limit exceeded"}
        )

    with pytest.raises(MeteoSourceError, match=r"HTTP 429 \(Minutely API request limit exceeded\)"):
        _client(handler).fetch_daily(0, 0, date(2020, 1, 1), date(2020, 1, 3))
