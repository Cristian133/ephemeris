from datetime import date

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.meteo import get_meteo_service
from app.main import app
from app.meteo.client import MeteoSourceError
from app.meteo.series import DailySeries

_BA = {"latitude": -34.6037, "longitude": -58.3816}


class FakeService:
    """Serie constante (2 mm de lluvia, 50 % de nubes, 6 h de sol y 15 MJ/m² por día) en
    todos los años pedidos; registra lo que le piden."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[float, float, int, int]] = []
        self.elevation: float | None = 20.0
        self.elevation_error: Exception | None = None

    def cell_elevation(self, latitude: float, longitude: float) -> float | None:
        if self.elevation_error:
            raise self.elevation_error
        return self.elevation

    def daily(self, latitude: float, longitude: float, first_year: int, last_year: int):
        self.calls.append((latitude, longitude, first_year, last_year))
        if self.error:
            raise self.error
        dates = np.arange(
            np.datetime64(f"{first_year}-01-01"),
            np.datetime64(f"{last_year + 1}-01-01"),
            dtype="datetime64[D]",
        )
        rain = np.full(len(dates), 2.0)
        cloud = np.full(len(dates), 50.0)
        sunshine = np.full(len(dates), 6 * 3600.0)
        radiation = np.full(len(dates), 15.0)  # MJ/m² por día (~4.17 kWh)
        return DailySeries(dates, rain, cloud, sunshine, radiation)


@pytest.fixture
def service():
    fake = FakeService()
    app.dependency_overrides[get_meteo_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


client = TestClient(app)


def test_lluvia_uses_the_climatological_period_by_default(service: FakeService) -> None:
    response = client.get("/meteo/lluvia", params=_BA)
    assert response.status_code == 200
    assert service.calls == [(-34.6037, -58.3816, 1991, 2020)]
    body = response.json()
    assert (body["first_year"], body["last_year"]) == (1991, 2020)
    assert body["grid_latitude"] == pytest.approx(-34.5)
    assert body["grid_longitude"] == pytest.approx(-58.5)
    assert body["rainy_day_threshold_mm"] == 1.0
    assert "ERA5" in body["source"]


def test_lluvia_returns_twelve_months_and_the_annual_summary(service: FakeService) -> None:
    body = client.get("/meteo/lluvia", params={**_BA, "first_year": 2021, "last_year": 2022}).json()
    assert [m["month"] for m in body["months"]] == list(range(1, 13))
    january = body["months"][0]
    assert january["mean_mm"] == pytest.approx(62.0)  # 31 días x 2 mm
    assert january["years_with_data"] == 2
    assert january["mean_rainy_days"] == pytest.approx(31.0)
    assert body["annual"]["mean_mm"] == pytest.approx(730.0)
    assert [y["year"] for y in body["yearly_totals"]] == [2021, 2022]
    assert body["wettest_year"]["total_mm"] == pytest.approx(730.0)


def test_lluvia_rejects_out_of_range_parameters(service: FakeService) -> None:
    assert client.get("/meteo/lluvia", params={**_BA, "latitude": 91}).status_code == 422
    assert client.get("/meteo/lluvia", params={**_BA, "first_year": 1900}).status_code == 422
    assert service.calls == []


def test_lluvia_maps_service_errors(service: FakeService) -> None:
    service.error = ValueError("Solo hay estadísticas de años ya terminados")
    response = client.get("/meteo/lluvia", params={**_BA, "last_year": date.today().year})
    assert response.status_code == 422
    assert "terminados" in response.json()["detail"]

    service.error = MeteoSourceError("Open-Meteo no disponible")
    assert client.get("/meteo/lluvia", params=_BA).status_code == 502


def test_nubosidad_summarises_cloud_cover_and_day_types(service: FakeService) -> None:
    response = client.get("/meteo/nubosidad", params={**_BA, "first_year": 2021, "last_year": 2022})
    assert response.status_code == 200
    body = response.json()
    assert (body["clear_max_pct"], body["overcast_min_pct"]) == (20.0, 80.0)
    assert [m["month"] for m in body["months"]] == list(range(1, 13))
    january = body["months"][0]
    assert january["mean_pct"] == pytest.approx(50.0)
    assert january["years_with_data"] == 2
    assert (january["clear_days"], january["partly_days"], january["overcast_days"]) == (0, 31, 0)
    assert body["annual"]["mean_pct"] == pytest.approx(50.0)
    assert body["grid_latitude"] == pytest.approx(-34.5)


def test_horas_sol_compares_actual_with_astronomical_hours(service: FakeService) -> None:
    body = client.get(
        "/meteo/horas-sol", params={**_BA, "first_year": 2021, "last_year": 2022}
    ).json()
    december, june = body["months"][11], body["months"][5]
    assert december["mean_hours"] == pytest.approx(6.0)
    assert 14.0 < december["astronomical_hours"] < 14.6  # verano austral
    assert 9.6 < june["astronomical_hours"] < 10.3
    assert december["relative_pct"] == pytest.approx(6 / december["astronomical_hours"] * 100)
    assert june["relative_pct"] > december["relative_pct"]  # el mismo sol rinde más de día corto
    annual = body["annual"]
    assert annual["mean_hours"] == pytest.approx(6 * 365)
    assert 4300 < annual["astronomical_hours"] < 4500
    assert annual["relative_pct"] == pytest.approx(
        annual["mean_hours"] / annual["astronomical_hours"] * 100
    )


@pytest.mark.parametrize("path", ["/meteo/nubosidad", "/meteo/horas-sol"])
def test_new_endpoints_map_service_errors(service: FakeService, path: str) -> None:
    service.error = ValueError("Solo hay estadísticas de años ya terminados")
    assert client.get(path, params=_BA).status_code == 422
    service.error = MeteoSourceError("Open-Meteo no disponible")
    assert client.get(path, params=_BA).status_code == 502


def test_irradiancia_real_compares_real_and_clear_sky(service: FakeService) -> None:
    body = client.get(
        "/meteo/irradiancia-real", params={**_BA, "first_year": 2021, "last_year": 2022}
    ).json()
    january, june = body["months"][0], body["months"][5]
    assert january["mean_kwh"] == pytest.approx(15 / 3.6)
    assert january["clear_sky_kwh"] > june["clear_sky_kwh"]  # verano austral
    assert january["clearness_index"] == pytest.approx(
        january["mean_kwh"] / january["clear_sky_kwh"]
    )
    assert june["clearness_index"] > january["clearness_index"]  # misma radiación, menos techo
    annual = body["annual"]
    assert annual["mean_kwh"] == pytest.approx(15 / 3.6 * 365)
    assert 2000 < annual["clear_sky_kwh"] < 2300
    assert (body["elevation_m"], body["elevation_source"]) == (20.0, "cell")
    assert body["linke_turbidity"] == 3.0


def test_irradiancia_real_estimates_the_panel_with_the_real_sky(service: FakeService) -> None:
    body = client.get(
        "/meteo/irradiancia-real", params={**_BA, "first_year": 2021, "last_year": 2022}
    ).json()
    panel = body["panel"]
    assert panel["azimuth_deg"] == 0.0  # hemisferio sur: mira al norte
    assert 15 < panel["tilt_deg"] < 50
    assert 0 < panel["estimated_kwh_per_m2"] < panel["clear_sky_kwh_per_m2"] * 1.3
    assert panel["albedo"] == 0.2


def test_irradiancia_real_uses_the_requested_atmosphere(service: FakeService) -> None:
    base = client.get("/meteo/irradiancia-real", params={**_BA, "elevation_m": 0}).json()
    assert (base["elevation_m"], base["elevation_source"]) == (0.0, "user")
    hazy = client.get(
        "/meteo/irradiancia-real", params={**_BA, "elevation_m": 0, "linke_turbidity": 6}
    ).json()
    mountain = client.get("/meteo/irradiancia-real", params={**_BA, "elevation_m": 3000}).json()
    assert hazy["annual"]["clear_sky_kwh"] < base["annual"]["clear_sky_kwh"]
    assert mountain["annual"]["clear_sky_kwh"] > base["annual"]["clear_sky_kwh"]
    assert client.get("/meteo/irradiancia-real", params={**_BA, "albedo": 2}).status_code == 422


def test_irradiancia_real_maps_service_errors(service: FakeService) -> None:
    service.error = MeteoSourceError("Open-Meteo no disponible")
    assert client.get("/meteo/irradiancia-real", params=_BA).status_code == 502


def test_irradiancia_real_uses_the_cell_elevation_by_default(service: FakeService) -> None:
    service.elevation = 3000.0
    high = client.get("/meteo/irradiancia-real", params=_BA).json()
    service.elevation = 0.0
    sea = client.get("/meteo/irradiancia-real", params=_BA).json()
    assert high["elevation_m"] == 3000.0 and high["elevation_source"] == "cell"
    assert high["annual"]["clear_sky_kwh"] > sea["annual"]["clear_sky_kwh"]
    # Con el mismo dato real y un techo más alto, el índice de claridad baja.
    assert high["annual"]["clearness_index"] < sea["annual"]["clearness_index"]


def test_an_explicit_elevation_wins_over_the_cell_one(service: FakeService) -> None:
    service.elevation = 3000.0
    body = client.get("/meteo/irradiancia-real", params={**_BA, "elevation_m": 100}).json()
    assert (body["elevation_m"], body["elevation_source"]) == (100.0, "user")


def test_falls_back_to_sea_level_when_the_elevation_is_unavailable(service: FakeService) -> None:
    service.elevation_error = MeteoSourceError("sin red")
    response = client.get("/meteo/irradiancia-real", params=_BA)
    assert response.status_code == 200  # los datos estaban en el caché: no se rechaza
    assert (response.json()["elevation_m"], response.json()["elevation_source"]) == (0.0, "default")
    service.elevation_error = None
    service.elevation = None  # la fuente no la informa
    assert client.get("/meteo/irradiancia-real", params=_BA).json()["elevation_source"] == "default"


def test_cell_elevation_is_clamped_to_the_supported_range(service: FakeService) -> None:
    service.elevation = 12000.0
    body = client.get("/meteo/irradiancia-real", params=_BA).json()
    assert body["elevation_m"] == 9000.0


def test_horas_sol_adds_the_estimate_from_radiation(service: FakeService) -> None:
    body = client.get(
        "/meteo/horas-sol", params={**_BA, "first_year": 2021, "last_year": 2022}
    ).json()
    assert (body["angstrom_a"], body["angstrom_b"]) == (0.27, 0.51)
    for month in body["months"]:
        # En junio la radiación del dato de prueba roza el techo y la estimación
        # se corta en el día completo, de ahí el `<=`.
        assert 0 < month["estimated_mean_hours"] <= month["astronomical_hours"]
        assert month["estimated_relative_pct"] == pytest.approx(
            month["estimated_mean_hours"] / month["astronomical_hours"] * 100
        )
        assert (
            month["estimated_p10_hours"]
            <= month["estimated_mean_hours"]
            <= month["estimated_p90_hours"]
        )
        assert month["mean_hours"] == pytest.approx(6.0)  # el modelo del reanálisis, intacto
    annual = body["annual"]
    assert annual["estimated_mean_hours"] == pytest.approx(
        sum(m["estimated_mean_hours"] * d for m, d in zip(body["months"], _DAYS, strict=True)),
        rel=0.01,
    )
    assert annual["estimated_relative_pct"] == pytest.approx(
        annual["estimated_mean_hours"] / annual["astronomical_hours"] * 100
    )
    assert annual["mean_hours"] == pytest.approx(6 * 365)


_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
