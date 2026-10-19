import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_anual_returns_one_entry_per_day_of_leap_year() -> None:
    response = client.get(
        "/sol/anual", params={"latitude": -34.6, "longitude": -58.4, "year": 2024}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == -34.6
    assert body["longitude"] == -58.4
    assert body["year"] == 2024
    assert len(body["days"]) == 366  # 2024 es bisiesto
    assert body["days"][0]["date"] == "2024-01-01"
    assert body["days"][-1]["date"] == "2024-12-31"


def test_anual_non_leap_year_has_365_days() -> None:
    response = client.get("/sol/anual", params={"latitude": 0.0, "longitude": 0.0, "year": 2023})
    assert response.status_code == 200
    assert len(response.json()["days"]) == 365


def test_anual_equatorial_day_length_close_to_12_hours() -> None:
    response = client.get("/sol/anual", params={"latitude": 0.0, "longitude": 0.0, "year": 2024})
    assert response.status_code == 200
    for day in response.json()["days"]:
        assert day["day_length_hours"] is not None
        assert 11.9 < day["day_length_hours"] < 12.3
        assert day["always_above"] is None


def test_anual_high_latitude_includes_polar_day_and_night() -> None:
    response = client.get("/sol/anual", params={"latitude": 80.0, "longitude": 0.0, "year": 2024})
    assert response.status_code == 200
    days = response.json()["days"]

    polar_days = [d for d in days if d["sunrise"] is None]
    assert any(d["always_above"] is True for d in polar_days)  # sol de medianoche
    assert any(d["always_above"] is False for d in polar_days)  # noche polar

    normal_days = [d for d in days if d["sunrise"] is not None]
    assert normal_days  # también hay días con orto/ocaso normal
    for day in normal_days:
        assert day["day_length_hours"] is not None
        assert day["always_above"] is None


def test_anual_rejects_out_of_range_latitude() -> None:
    response = client.get("/sol/anual", params={"latitude": 91.0, "longitude": 0.0, "year": 2024})
    assert response.status_code == 422


def test_anual_rejects_out_of_range_longitude() -> None:
    response = client.get("/sol/anual", params={"latitude": 0.0, "longitude": 200.0, "year": 2024})
    assert response.status_code == 422


def test_anual_requires_all_query_params() -> None:
    response = client.get("/sol/anual", params={"latitude": 0.0, "longitude": 0.0})
    assert response.status_code == 422


def test_trayectoria_returns_default_96_samples_covering_the_day() -> None:
    response = client.get(
        "/sol/trayectoria",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == -34.6
    assert body["longitude"] == -58.4
    assert body["date"] == "2024-06-01"
    assert len(body["samples"]) == 96
    assert body["samples"][0]["time"] == "2024-06-01T00:00:00Z"
    assert body["samples"][-1]["time"] == "2024-06-01T23:45:00Z"
    for sample in body["samples"]:
        assert -90 <= sample["altitude"] <= 90
        assert sample["apparent_altitude"] >= sample["altitude"]  # la refracción siempre "levanta"
        assert 0 <= sample["azimuth"] < 360


def test_trayectoria_respects_custom_num_samples() -> None:
    response = client.get(
        "/sol/trayectoria",
        params={"latitude": 0.0, "longitude": 0.0, "date": "2024-03-20", "num_samples": 24},
    )
    assert response.status_code == 200
    assert len(response.json()["samples"]) == 24


def test_trayectoria_rejects_num_samples_out_of_range() -> None:
    response = client.get(
        "/sol/trayectoria",
        params={"latitude": 0.0, "longitude": 0.0, "date": "2024-03-20", "num_samples": 1000},
    )
    assert response.status_code == 422


def test_trayectoria_rejects_out_of_range_latitude() -> None:
    response = client.get(
        "/sol/trayectoria",
        params={"latitude": 91.0, "longitude": 0.0, "date": "2024-03-20"},
    )
    assert response.status_code == 422


def test_trayectoria_requires_date() -> None:
    response = client.get("/sol/trayectoria", params={"latitude": 0.0, "longitude": 0.0})
    assert response.status_code == 422


def test_dia_returns_normal_day() -> None:
    response = client.get(
        "/sol/dia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == -34.6
    assert body["longitude"] == -58.4
    assert body["date"] == "2024-06-01"
    assert body["sunrise"] is not None
    assert body["sunset"] is not None
    assert body["day_length_hours"] is not None
    assert body["always_above"] is None


def test_dia_polar_night_has_no_sunrise_or_sunset() -> None:
    response = client.get(
        "/sol/dia",
        params={"latitude": 80.0, "longitude": 0.0, "date": "2024-12-21"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sunrise"] is None
    assert body["sunset"] is None
    assert body["day_length_hours"] is None
    assert body["always_above"] is False


def test_dia_matches_anual_same_day() -> None:
    dia_response = client.get(
        "/sol/dia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    anual_response = client.get(
        "/sol/anual", params={"latitude": -34.6, "longitude": -58.4, "year": 2024}
    )
    day_from_year = next(d for d in anual_response.json()["days"] if d["date"] == "2024-06-01")
    assert dia_response.json()["transit"] == day_from_year["transit"]
    assert dia_response.json()["sunrise"] == day_from_year["sunrise"]
    assert dia_response.json()["sunset"] == day_from_year["sunset"]


def test_dia_rejects_out_of_range_longitude() -> None:
    response = client.get(
        "/sol/dia", params={"latitude": 0.0, "longitude": -200.0, "date": "2024-06-01"}
    )
    assert response.status_code == 422


def test_mediodia_returns_transit_altitude_and_azimuth() -> None:
    response = client.get(
        "/sol/mediodia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == -34.6
    assert body["longitude"] == -58.4
    assert body["date"] == "2024-06-01"
    assert body["transit"] is not None
    assert -90 <= body["altitude_deg"] <= 90
    assert body["apparent_altitude_deg"] >= body["altitude_deg"]
    assert 0 <= body["azimuth_deg"] < 360


def test_mediodia_matches_dia_transit() -> None:
    mediodia_response = client.get(
        "/sol/mediodia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    dia_response = client.get(
        "/sol/dia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    assert mediodia_response.json()["transit"] == dia_response.json()["transit"]


def test_mediodia_azimuth_is_north_in_buenos_aires_december() -> None:
    response = client.get(
        "/sol/mediodia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-12-21"},
    )
    assert response.status_code == 200
    assert response.json()["azimuth_deg"] == pytest.approx(0.0, abs=1e-4)


def test_mediodia_requires_date() -> None:
    response = client.get("/sol/mediodia", params={"latitude": 0.0, "longitude": 0.0})
    assert response.status_code == 422


def test_irradiancia_returns_samples_and_positive_energy() -> None:
    response = client.get(
        "/sol/irradiancia",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-06-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == -34.6
    assert body["longitude"] == -58.4
    assert body["date"] == "2024-06-01"
    assert body["energy_wh_per_m2"] > 0
    assert len(body["samples"]) == 96
    assert all(s["power_w_per_m2"] >= 0 for s in body["samples"])
    assert any(s["power_w_per_m2"] == 0 for s in body["samples"])  # de noche
    assert any(s["power_w_per_m2"] > 0 for s in body["samples"])  # de día


def test_irradiancia_zero_energy_during_polar_night() -> None:
    response = client.get(
        "/sol/irradiancia",
        params={"latitude": 80.0, "longitude": 0.0, "date": "2024-12-21"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["energy_wh_per_m2"] == 0.0
    assert all(s["power_w_per_m2"] == 0.0 for s in body["samples"])


def test_irradiancia_respects_custom_num_samples() -> None:
    response = client.get(
        "/sol/irradiancia",
        params={"latitude": 0.0, "longitude": 0.0, "date": "2024-03-20", "num_samples": 24},
    )
    assert response.status_code == 200
    assert len(response.json()["samples"]) == 24


def test_irradiancia_rejects_out_of_range_latitude() -> None:
    response = client.get(
        "/sol/irradiancia",
        params={"latitude": 91.0, "longitude": 0.0, "date": "2024-03-20"},
    )
    assert response.status_code == 422


def test_irradiancia_requires_date() -> None:
    response = client.get("/sol/irradiancia", params={"latitude": 0.0, "longitude": 0.0})
    assert response.status_code == 422


def test_crepusculos_returns_all_crossings() -> None:
    response = client.get(
        "/sol/crepusculos",
        params={"latitude": -34.6, "longitude": -58.4, "date": "2024-03-20"},
    )
    assert response.status_code == 200
    body = response.json()
    for key in (
        "astronomical",
        "nautical",
        "civil",
        "blue_hour_limit",
        "horizon",
        "golden_hour_limit",
    ):
        assert body[key]["rise"] is not None
        assert body[key]["set"] is not None
    assert body["civil"]["altitude_deg"] == -6.0
    assert body["civil"]["rise"] < body["horizon"]["rise"]


def test_estaciones_returns_four_events_in_order() -> None:
    response = client.get("/sol/estaciones", params={"year": 2024})
    assert response.status_code == 200
    body = response.json()
    events = [
        body["march_equinox"],
        body["june_solstice"],
        body["september_equinox"],
        body["december_solstice"],
    ]
    assert events == sorted(events)
    assert body["march_equinox"].startswith("2024-03-20")


def test_estaciones_rejects_year_outside_range() -> None:
    assert client.get("/sol/estaciones", params={"year": 500}).status_code == 422


def test_panel_returns_orientation_and_curve() -> None:
    response = client.get(
        "/sol/panel", params={"latitude": -34.6, "longitude": -58.4, "year": 2024}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["azimuth_deg"] == 0.0
    assert 0 < body["annual_tilt_deg"] < 60
    assert len(body["curve"]) == 19
    assert body["annual_kwh_per_m2"] > body["horizontal_kwh_per_m2"]
