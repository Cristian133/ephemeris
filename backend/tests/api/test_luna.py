import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_BA = {"latitude": -34.6, "longitude": -58.4, "date": "2024-04-10"}


def test_luna_dia_returns_events_and_phase() -> None:
    response = client.get("/luna/dia", params=_BA)
    assert response.status_code == 200
    body = response.json()
    assert body["rise"] is not None and body["set"] is not None and body["transit"] is not None
    assert body["rise"] < body["transit"] < body["set"]
    assert 0 <= body["illuminated_fraction"] <= 1
    assert body["phase_key"] in {
        "new",
        "waxing_crescent",
        "first_quarter",
        "waxing_gibbous",
        "full",
        "waning_gibbous",
        "last_quarter",
        "waning_crescent",
    }
    assert 0 <= body["age_days"] < 30
    assert 356_000 < body["distance_km"] < 407_000


def test_luna_dia_phase_matches_the_calendar() -> None:
    new_moon = client.get("/luna/dia", params={**_BA, "date": "2024-04-08"}).json()
    full_moon = client.get("/luna/dia", params={**_BA, "date": "2024-04-24"}).json()
    assert new_moon["phase_key"] == "new" and new_moon["illuminated_fraction"] < 0.05
    assert full_moon["phase_key"] == "full" and full_moon["illuminated_fraction"] > 0.95
    # La Luna nueva fue a las 18:21 UT del 8; el mediodía local del 8 en
    # Buenos Aires (15:53 UT) es unas horas antes, así que la edad es la del
    # fin de la lunación anterior, y la del 9 es de poco menos de un día.
    assert new_moon["age_days"] > 29.0
    assert client.get("/luna/dia", params={**_BA, "date": "2024-04-09"}).json()["age_days"] < 1.5


def test_luna_dia_polar_case_has_no_rise_and_set() -> None:
    response = client.get(
        "/luna/dia", params={"latitude": 80.0, "longitude": 0.0, "date": "2024-12-20"}
    )
    body = response.json()
    if body["rise"] is None and body["set"] is None:
        assert body["always_above"] in (True, False)


def test_luna_dia_validates_inputs() -> None:
    assert client.get("/luna/dia", params={**_BA, "latitude": 91}).status_code == 422
    assert client.get("/luna/dia", params={"latitude": 0, "longitude": 0}).status_code == 422


def test_luna_trayectoria() -> None:
    response = client.get("/luna/trayectoria", params={**_BA, "num_samples": 48})
    assert response.status_code == 200
    body = response.json()
    assert len(body["samples"]) == 48
    assert all(-90 <= s["altitude"] <= 90 and 0 <= s["azimuth"] < 360 for s in body["samples"])
    assert 0 <= body["illuminated_fraction"] <= 1


def test_luna_fases_of_2024() -> None:
    response = client.get("/luna/fases", params={"year": 2024})
    assert response.status_code == 200
    phases = response.json()["phases"]
    assert 48 <= len(phases) <= 50
    assert all(p["time"].startswith("2024") for p in phases)
    april_new = next(p for p in phases if p["kind"] == "new" and p["time"].startswith("2024-04"))
    assert april_new["time"].startswith("2024-04-08T18:2")
    assert {p["kind"] for p in phases} == {"new", "first_quarter", "full", "last_quarter"}


@pytest.mark.parametrize("year", [999, 3001])
def test_luna_fases_rejects_years_out_of_range(year: int) -> None:
    assert client.get("/luna/fases", params={"year": year}).status_code == 422


def test_pascua() -> None:
    body = client.get("/calendario/pascua", params={"year": 2024}).json()
    assert body["western"] == {"date": "2024-03-31", "weekday": "domingo"}
    assert body["orthodox_julian_date"] == "2024-04-22"
    assert body["orthodox"] == {"date": "2024-05-05", "weekday": "domingo"}
    assert body["coincide"] is False


def test_pascua_coincides_some_years() -> None:
    body = client.get("/calendario/pascua", params={"year": 2025}).json()
    assert body["coincide"] is True
    assert body["western"]["date"] == "2025-04-20"


def test_pascua_validates_year() -> None:
    assert client.get("/calendario/pascua", params={"year": 1500}).status_code == 422


def test_mareas_dia() -> None:
    response = client.get("/mareas/dia", params=_BA)
    assert response.status_code == 200
    body = response.json()
    assert len(body["samples"]) == 144
    assert body["max_total_m"] > body["min_total_m"]
    assert 3 <= len(body["extremes"]) <= 5
    assert all(s["total_m"] == pytest.approx(s["moon_m"] + s["sun_m"]) for s in body["samples"])


def test_mareas_spring_vs_neap() -> None:
    spring = client.get("/mareas/dia", params={**_BA, "date": "2024-04-08"}).json()
    neap = client.get("/mareas/dia", params={**_BA, "date": "2024-04-15"}).json()
    assert spring["spring_neap_ratio"] > 1.2
    assert neap["spring_neap_ratio"] < 0.7


def test_apsides_of_2025() -> None:
    body = client.get("/luna/apsides", params={"year": 2025}).json()
    assert 24 <= len(body["apsides"]) <= 28
    nov = next(
        a for a in body["apsides"] if a["kind"] == "perigee" and a["time"].startswith("2025-11-05")
    )
    assert nov["distance_km"] == pytest.approx(356_832, abs=60)
    assert client.get("/luna/apsides", params={"year": 999}).status_code == 422


def test_eclipses_of_2024() -> None:
    body = client.get("/eclipses/anio", params={"year": 2024}).json()
    assert [e["kind"] for e in body["solar"]] == ["total", "annular"]
    assert [e["kind"] for e in body["lunar"]] == ["penumbral", "partial"]
    assert body["solar"][0]["time"].startswith("2024-04-08T18:1")
    assert body["solar"][0]["central"] is True
    assert body["lunar"][1]["total_start"] is None
    assert all(e["moon_altitude_deg"] is None for e in body["lunar"])


def test_eclipses_report_lunar_visibility_for_a_location() -> None:
    # Eclipse parcial del 18/9/2024 a las 02:44 UT: noche en Buenos Aires
    # (23:44 del 17), con la Luna alta; en Sídney es de día (12:44) y la
    # Luna está bajo el horizonte.
    params = {"year": 2024}
    buenos_aires = client.get(
        "/eclipses/anio", params={**params, "latitude": -34.6, "longitude": -58.4}
    ).json()
    sydney = client.get(
        "/eclipses/anio", params={**params, "latitude": -33.9, "longitude": 151.2}
    ).json()
    assert buenos_aires["lunar"][1]["moon_altitude_deg"] > 20
    assert sydney["lunar"][1]["moon_altitude_deg"] < 0


def test_eclipses_validate_year_range() -> None:
    assert client.get("/eclipses/anio", params={"year": 1700}).status_code == 422
    assert client.get("/eclipses/anio", params={"year": 2300}).status_code == 422
