"""Contrasta lo que calcula la etapa 3 con normales medidas en estaciones.

Compara la lluvia anual y las horas de sol anuales del reanálisis (ERA5 vía
Open-Meteo) con las normales publicadas por el SMN y la AEMET, y las horas de
sol estimadas desde la radiación (Ångström-Prescott) con los coeficientes de
FAO-56 y con los calibrados. Usa la red (la primera vez baja 30 años por
estación) y el caché local; si Open-Meteo corta por exceso de llamadas por
minuto, espera y reintenta.

    cd backend && .venv/bin/python scripts/validar_estaciones.py [archivo.sqlite]
    cd backend && .venv/bin/python scripts/validar_estaciones.py --ajustar [archivo.sqlite]
    cd backend && .venv/bin/python scripts/validar_estaciones.py --radiacion [archivo.sqlite]

`--ajustar` recalcula los coeficientes a y b con todas las estaciones y los
valida dejando una estación afuera cada vez (validación cruzada).

`--radiacion` contrasta la radiación con la medida por la red solarimétrica de
GERSolar (UNLu) e INTA en la Pampa Húmeda (piranómetros de primera calidad,
2010-2018): la distribución de los días según su índice de claridad kt. Las
coordenadas de los seis puntos son aproximadas (no se pudo confirmar la lista
de estaciones de la red) y los porcentajes medidos son los de toda la red.

Las referencias vienen de las tablas climáticas de Wikipedia, que citan al SMN y a
la AEMET. Son fuentes secundarias, con períodos distintos en las horas de sol
(ver `sun_note`), y alguna página avisa que puede tener texto sin verificar:
conviene cotejarlas con los portales oficiales antes de citarlas. Ver
docs/plan_tecnico.md, sección 7.3.
"""

import calendar
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.meteo.aggregate import monthly_table  # noqa: E402
from app.meteo.client import MeteoSourceError, OpenMeteoArchiveClient  # noqa: E402
from app.meteo.grid import cell_for  # noqa: E402
from app.meteo.rain import rain_statistics  # noqa: E402
from app.meteo.series import DailySeries  # noqa: E402
from app.meteo.service import MeteoService  # noqa: E402
from app.meteo.sky import (  # noqa: E402
    ANGSTROM_A,
    ANGSTROM_B,
    DAYS_IN_MONTH,
    FAO_ANGSTROM_A,
    FAO_ANGSTROM_B,
    REFERENCE_YEAR,
    astronomical_daylight_hours,
    estimated_sunshine_statistics,
    sunshine_statistics,
)
from app.meteo.store import MeteoStore  # noqa: E402
from app.solar.insolation import extraterrestrial_daily_kwh  # noqa: E402

PERIOD = (1991, 2020)
_DAYS = np.array(DAYS_IN_MONTH)
_RETRY_WAIT_S = 65  # Open-Meteo limita por minuto
_MAX_ATTEMPTS = 6


@dataclass(frozen=True)
class Station:
    latitude: float
    longitude: float
    rain_mm: float  # lluvia anual medida
    sunshine_h: tuple[float, ...]  # horas de sol medidas de enero a diciembre
    sun_note: str  # de qué período/fuente salen las horas de sol


STATIONS = {
    "Buenos Aires, Obs. Central (SMN)": Station(
        -34.5822,
        -58.4833,
        1257.6,
        (272.8, 223.2, 217.0, 168.0, 158.1, 135.0, 142.6, 170.5, 180.0, 204.6, 246.0, 266.6),
        "SMN 1991-2020",
    ),
    "Córdoba, Observatorio (SMN)": Station(
        -31.4,
        -64.19,
        815.6,
        (248.0, 220.4, 226.3, 195.0, 173.6, 165.0, 189.1, 220.1, 216.0, 232.5, 240.0, 235.6),
        "SMN 1991-2020; la página avisa de texto sin verificar",
    ),
    "Madrid, Retiro (AEMET)": Station(
        40.41,
        -3.68,
        416.0,
        (149, 158, 211, 230, 268, 315, 355, 332, 259, 199, 144, 124),
        "AEMET 1981-2010",
    ),
    "Mendoza, Aeropuerto (SMN)": Station(
        -32.83,
        -68.79,
        238.0,
        (316.2, 257.1, 241.8, 210.0, 189.1, 183.0, 204.6, 232.5, 228.0, 275.9, 309.0, 328.6),
        "SMN 1991-2020; el Observatorio de la misma ciudad da 2636 h (13 % menos)",
    ),
    "Tucumán (SMN)": Station(
        -26.84,
        -65.10,
        1009.7,
        (229.4, 186.5, 173.6, 153.0, 145.7, 135.0, 186.0, 204.6, 198.0, 195.3, 213.0, 229.4),
        "SMN, horas de sol 1991-2000; julio mayor que junio, llamativo",
    ),
    "Ushuaia, Aeropuerto (SMN)": Station(
        -54.84,
        -68.31,
        457.8,
        (164.3, 146.9, 127.1, 96.0, 77.5, 45.0, 58.9, 93.0, 126.0, 155.0, 159.0, 155.0),
        "SMN; la página cita 1901-1990 para el porcentaje de sol",
    ),
    "Salta, Aeropuerto (SMN)": Station(
        -24.85,
        -65.49,
        738.3,
        (195.3, 166.7, 158.1, 159.0, 158.1, 171.0, 204.6, 223.2, 210.0, 210.8, 213.0, 217.0),
        "SMN, horas de sol 1991-2000",
    ),
    "Bariloche, Aeropuerto (SMN)": Station(
        -41.15,
        -71.16,
        812.5,
        (334.7, 283.3, 241.6, 183.7, 130.4, 96.0, 124.7, 146.9, 189.9, 239.3, 290.7, 296.3),
        "OMM 1981-2010; la suma mensual (2558) difiere del total que da la página (2595)",
    ),
}


def _daily(service: MeteoService, station: Station) -> DailySeries:
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return service.daily(station.latitude, station.longitude, *PERIOD)
        except MeteoSourceError as error:
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            print(f"  ({error}); espero {_RETRY_WAIT_S} s", flush=True)
            time.sleep(_RETRY_WAIT_S)
    raise AssertionError("inalcanzable")


def _diff(value: float, reference: float) -> str:
    return f"{value:6.0f} ({(value / reference - 1) * 100:+4.0f} %)"


def _monthly_clearness(series: DailySeries, extraterrestrial: np.ndarray) -> np.ndarray:
    """Índice de claridad medio de cada mes (radiación real sobre extraterrestre)."""
    bounds = np.cumsum((0, *DAYS_IN_MONTH))
    et = np.array([extraterrestrial[bounds[m] : bounds[m + 1]].mean() for m in range(12)])
    _, radiation = monthly_table(series.dates, series.radiation_mj_m2 / 3.6, "mean")
    return np.nanmean(radiation, axis=0) / et


def comparar(service: MeteoService) -> None:
    print(f"Período {PERIOD[0]}-{PERIOD[1]}; entre paréntesis, la diferencia con lo medido.")
    print(
        f"Coeficientes: calibrados a={ANGSTROM_A}, b={ANGSTROM_B}; "
        f"FAO-56 a={FAO_ANGSTROM_A}, b={FAO_ANGSTROM_B}\n"
    )
    header = (
        f"{'Estación':34} {'Lluvia med.':>11} {'ERA5':>14} | {'Sol med.':>8} "
        f"{'Modelo ERA5':>14} {'FAO-56':>14} {'Calibrado':>14}"
    )
    print(header)
    rain_errors, calibrated_errors, fao_errors = [], [], []
    for name, st in STATIONS.items():
        series = _daily(service, st)
        cell = cell_for(st.latitude, st.longitude)
        daylight = astronomical_daylight_hours(cell.latitude, cell.longitude)
        et = extraterrestrial_daily_kwh(REFERENCE_YEAR, cell.latitude, cell.longitude)
        measured = sum(st.sunshine_h)
        model = sunshine_statistics(series, daylight).annual_hours.mean
        fao = estimated_sunshine_statistics(
            series, et, daylight, FAO_ANGSTROM_A, FAO_ANGSTROM_B
        ).annual_hours.mean
        calibrated = estimated_sunshine_statistics(series, et, daylight).annual_hours.mean
        rain = rain_statistics(series).annual.mean
        assert None not in (model, fao, calibrated, rain)
        rain_errors.append(rain / st.rain_mm - 1)
        fao_errors.append(fao / measured - 1)
        calibrated_errors.append(calibrated / measured - 1)
        print(
            f"{name:34} {st.rain_mm:11.0f} {_diff(rain, st.rain_mm):>14} | {measured:8.0f} "
            f"{_diff(model, measured):>14} {_diff(fao, measured):>14} "
            f"{_diff(calibrated, measured):>14}"
        )
    print(
        f"\nError medio absoluto: lluvia {np.mean(np.abs(rain_errors)) * 100:.0f} % "
        f"(sesgo {np.mean(rain_errors) * 100:+.0f} %), horas de sol FAO-56 "
        f"{np.mean(np.abs(fao_errors)) * 100:.0f} %, "
        f"calibradas {np.mean(np.abs(calibrated_errors)) * 100:.0f} %."
    )
    print("\nNotas sobre la referencia de horas de sol:")
    for name, st in STATIONS.items():
        print(f"  {name}: {st.sun_note}")


def ajustar(service: MeteoService) -> None:
    """Regresión de kt sobre la fracción de sol medida, y validación cruzada."""
    data = {}
    for name, st in STATIONS.items():
        series = _daily(service, st)
        cell = cell_for(st.latitude, st.longitude)
        daylight = astronomical_daylight_hours(cell.latitude, cell.longitude)
        et = extraterrestrial_daily_kwh(REFERENCE_YEAR, cell.latitude, cell.longitude)
        measured = np.array(st.sunshine_h)
        data[name] = (
            _monthly_clearness(series, et),
            measured / (daylight * _DAYS),
            daylight,
            measured,
        )

    def fit(names: list[str]) -> tuple[float, float]:
        kt = np.concatenate([data[n][0] for n in names])
        fraction = np.concatenate([data[n][1] for n in names])
        b, a = np.polyfit(fraction, kt, 1)
        return float(a), float(b)

    def annual_error(name: str, a: float, b: float) -> float:
        kt, _, daylight, measured = data[name]
        estimate = np.clip((kt - a) / b, 0.0, 1.0) * daylight * _DAYS
        return float(estimate.sum() / measured.sum() - 1)

    names = list(data)
    a, b = fit(names)
    print(f"Ajuste con las {len(names)} estaciones: a = {a:.3f}, b = {b:.3f} (a + b = {a + b:.2f})")
    print(f"Vigentes en el código: a = {ANGSTROM_A}, b = {ANGSTROM_B}\n")
    print(f"{'Estación':34} {'FAO-56':>8} {'Ajuste':>8} {'Validación cruzada':>20}")
    cross, fao_errs = [], []
    for name in names:
        a_cv, b_cv = fit([n for n in names if n != name])
        cross.append(annual_error(name, a_cv, b_cv))
        fao_errs.append(annual_error(name, FAO_ANGSTROM_A, FAO_ANGSTROM_B))
        print(
            f"{name:34} {fao_errs[-1] * 100:+7.0f}% {annual_error(name, a, b) * 100:+7.0f}% "
            f"{cross[-1] * 100:+19.0f}%"
        )
    print(
        f"\nError medio absoluto: FAO-56 {np.mean(np.abs(fao_errs)) * 100:.1f} %, "
        f"validación cruzada {np.mean(np.abs(cross)) * 100:.1f} % "
        f"(sesgo medio {np.mean(cross) * 100:+.1f} %)."
    )


# Porcentaje medido de días por clase de kt = irradiación diaria / extraterrestre
# (Grossi Gallegos et al.; GERSolar, "Nuevo atlas de radiación solar de la Pampa
# Húmeda argentina", resultados preliminares): cubierto, parcial con dominancia
# de difusa, parcial con dominancia de directa y despejado.
KT_EDGES = (0.3, 0.55, 0.7)
KT_MEASURED = (15.0, 24.0, 35.0, 26.0)
KT_LABELS = ("<0,3", "0,3-0,55", "0,55-0,7", ">=0,7")
KT_PERIOD = (2010, 2018)
PAMPA_POINTS = {
    "Luján": (-34.57, -59.10),
    "Pergamino": (-33.89, -60.57),
    "Paraná": (-31.85, -60.53),
    "Rafaela": (-31.20, -61.50),
    "Manfredi": (-31.85, -63.77),
    "Anguil": (-36.52, -63.99),
}


def _daily_clearness(series: DailySeries, latitude: float, longitude: float) -> np.ndarray:
    """kt de cada día: radiación real sobre la extraterrestre de ese día del año."""
    cell = cell_for(latitude, longitude)
    ceiling = {
        leap: extraterrestrial_daily_kwh(2020 if leap else 2021, cell.latitude, cell.longitude)
        for leap in (True, False)
    }
    days = series.dates.astype("datetime64[D]").astype(object)
    return np.array(
        [
            series.radiation_mj_m2[i]
            / 3.6
            / ceiling[calendar.isleap(day.year)][day.timetuple().tm_yday - 1]
            for i, day in enumerate(days)
        ]
    )


def _kt_classes(kt: np.ndarray) -> np.ndarray:
    kt = kt[~np.isnan(kt)]
    edges = np.digitize(kt, KT_EDGES)
    return np.array([(edges == i).mean() * 100 for i in range(len(KT_EDGES) + 1)])


def radiacion(service: MeteoService) -> None:
    print(f"Días por clase de kt, {KT_PERIOD[0]}-{KT_PERIOD[1]} (porcentaje de días).\n")
    print(f"{'':28}" + "".join(f"{label:>10}" for label in KT_LABELS) + "    kt medio")
    print(f"{'Medido (red GERSolar)':28}" + "".join(f"{v:9.0f}%" for v in KT_MEASURED))
    pooled = []
    for name, (lat, lon) in PAMPA_POINTS.items():
        for attempt in range(_MAX_ATTEMPTS):
            try:
                series = service.daily(lat, lon, *KT_PERIOD)
                break
            except MeteoSourceError as error:
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
                print(f"  ({error}); espero {_RETRY_WAIT_S} s", flush=True)
                time.sleep(_RETRY_WAIT_S)
        kt = _daily_clearness(series, lat, lon)
        pooled.append(kt)
        classes = _kt_classes(kt)
        print(
            f"{'ERA5, ' + name:28}"
            + "".join(f"{v:9.1f}%" for v in classes)
            + f"    {np.nanmean(kt):.3f}"
        )
    classes = _kt_classes(np.concatenate(pooled))
    print(f"{'ERA5, los seis juntos':28}" + "".join(f"{v:9.1f}%" for v in classes))
    gap = np.abs(classes - np.array(KT_MEASURED)).max()
    print(f"\nMayor diferencia con lo medido: {gap:.1f} puntos porcentuales.")


def main() -> None:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    db_path = args[0] if args else settings.meteo_db_path
    service = MeteoService(OpenMeteoArchiveClient(), MeteoStore(db_path))
    if "--ajustar" in sys.argv:
        ajustar(service)
    elif "--radiacion" in sys.argv:
        radiacion(service)
    else:
        comparar(service)


if __name__ == "__main__":
    main()
