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
    cd backend && .venv/bin/python scripts/validar_estaciones.py --asia [archivo.sqlite]

`--ajustar` recalcula los coeficientes a y b con las veinte estaciones y los
valida dejando una estación afuera cada vez (validación cruzada), y prueba si un
ajuste hecho con una región sirve en la otra (no sirve).

`--asia` compara con once ciudades de Japón (JMA, 1991-2020: horas de sol y
lluvia) y Hong Kong (HKO, 1991-2020: nubosidad, horas de sol, radiación global y
lluvia), y la nubosidad y la radiación de Hong Kong. Las coordenadas son
aproximadas. Estas estaciones entraron en el ajuste de a y b a partir de la
segunda versión; la primera, hecha solo con Argentina y Madrid, falló en ellas.

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


# Estaciones de Asia. Probaron fuera de muestra el primer ajuste de a y b (hecho solo
# con Argentina y Madrid) y fallaron; ahora entran en el ajuste.
# JMA ("Tables of Climatological Normals 1991-2020"): horas de sol y lluvia anual.
# HKO (King's Park, tabla 6 de las normales 1991-2020): horas de sol y lluvia.
_JMA = "JMA 1991-2020"
ASIA_STATIONS = {
    "Sapporo (JMA)": Station(
        43.06,
        141.33,
        1146.1,
        (90.4, 103.5, 144.7, 175.8, 200.4, 180.0, 168.0, 168.1, 159.3, 145.9, 99.1, 82.7),
        _JMA,
    ),
    "Sendai (JMA)": Station(
        38.26,
        140.90,
        1276.7,
        (149.0, 154.7, 178.6, 193.7, 191.9, 143.7, 126.3, 144.5, 128.0, 147.0, 143.4, 136.3),
        _JMA,
    ),
    "Niigata (JMA)": Station(
        37.89,
        139.03,
        1845.9,
        (56.4, 74.3, 136.8, 177.7, 202.8, 179.2, 162.1, 205.2, 156.2, 138.2, 91.5, 62.9),
        _JMA,
    ),
    "Nagoya (JMA)": Station(
        35.17,
        136.97,
        1578.9,
        (174.5, 175.5, 199.7, 200.2, 205.5, 151.8, 166.0, 201.3, 159.6, 168.9, 167.1, 170.3),
        _JMA,
    ),
    "Tokio (JMA)": Station(
        35.69,
        139.75,
        1598.2,
        (192.6, 170.4, 175.3, 178.8, 179.6, 124.2, 151.4, 174.2, 126.7, 129.4, 149.8, 174.4),
        _JMA,
    ),
    "Hiroshima (JMA)": Station(
        34.40,
        132.46,
        1572.2,
        (138.6, 140.1, 176.7, 191.9, 210.8, 154.6, 173.4, 207.3, 167.3, 178.6, 153.3, 140.6),
        _JMA,
    ),
    "Osaka (JMA)": Station(
        34.68,
        135.52,
        1338.3,
        (146.5, 140.6, 172.2, 192.6, 203.7, 154.3, 184.0, 222.4, 161.6, 166.1, 152.6, 152.1),
        _JMA,
    ),
    "Takamatsu (JMA)": Station(
        34.32,
        134.05,
        1150.1,
        (141.4, 143.8, 175.0, 194.5, 210.1, 158.2, 191.8, 221.2, 159.6, 164.6, 145.5, 142.7),
        _JMA,
    ),
    "Fukuoka (JMA)": Station(
        33.58,
        130.38,
        1686.9,
        (104.1, 123.5, 161.2, 188.1, 204.1, 145.2, 172.2, 200.9, 164.7, 175.9, 137.3, 112.2),
        _JMA,
    ),
    "Kagoshima (JMA)": Station(
        31.55,
        130.55,
        2434.7,
        (132.6, 139.3, 163.2, 175.6, 178.2, 109.3, 185.5, 206.9, 176.4, 184.0, 157.7, 143.2),
        _JMA,
    ),
    "Naha (JMA)": Station(
        26.21,
        127.69,
        2161.0,
        (93.1, 93.1, 115.3, 120.9, 138.2, 159.5, 227.0, 206.3, 181.3, 163.3, 121.7, 107.4),
        _JMA,
    ),
    "Hong Kong, King's Park (HKO)": Station(
        22.31,
        114.17,
        2431.2,
        (145.8, 101.7, 100.0, 113.2, 138.8, 144.3, 197.3, 182.1, 174.4, 197.8, 172.3, 161.6),
        "HKO 1991-2020",
    ),
}

# Hong Kong (HKO, tabla 6 de las normales 1991-2020): la nubosidad se observa en el
# Observatorio y la radiación se mide en King's Park, a pocos kilómetros.
HK_CLOUD_PCT = (62, 72, 77, 77, 76, 77, 72, 70, 66, 58, 58, 57)  # año: 68
HK_RADIATION_MJ = (
    10.55,
    10.24,
    10.71,
    12.52,
    14.46,
    14.61,
    17.22,
    15.73,
    14.99,
    14.52,
    12.26,
    10.91,
)


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


def comparar(service: MeteoService, stations: dict[str, Station] | None = None) -> None:
    stations = STATIONS if stations is None else stations
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
    for name, st in stations.items():
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
    for name, st in stations.items():
        print(f"  {name}: {st.sun_note}")


def ajustar(service: MeteoService) -> None:
    """Regresión de kt sobre la fracción de sol medida, y validación cruzada."""
    stations = {**STATIONS, **ASIA_STATIONS}
    data = {}
    for name, st in stations.items():
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

    def summary(label: str, a: float, b: float, names: list[str]) -> None:
        errors = np.array([annual_error(n, a, b) for n in names])
        print(
            f"  {label:38} a={a:.3f} b={b:.3f}  error medio {np.abs(errors).mean() * 100:4.1f} %  "
            f"sesgo {errors.mean() * 100:+5.1f} %  peor {np.abs(errors).max() * 100:3.0f} %"
        )

    names = list(data)
    south = list(STATIONS)  # Argentina y Madrid
    asia = list(ASIA_STATIONS)
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
    cross_errors = np.array(cross)
    print(
        f"\nError medio absoluto: FAO-56 {np.mean(np.abs(fao_errs)) * 100:.1f} %, "
        f"validación cruzada {np.abs(cross_errors).mean() * 100:.1f} % "
        f"(Argentina y Madrid {np.abs(cross_errors[: len(south)]).mean() * 100:.1f} %, "
        f"Asia {np.abs(cross_errors[len(south) :]).mean() * 100:.1f} %; "
        f"sesgo medio {cross_errors.mean() * 100:+.1f} %)."
    )

    print("\n¿Un ajuste hecho con una región sirve en la otra?")
    a_s, b_s = fit(south)
    a_a, b_a = fit(asia)
    summary("ajustado con Argentina y Madrid, en ellas", a_s, b_s, south)
    summary("ajustado con Argentina y Madrid, en Asia", a_s, b_s, asia)
    summary("ajustado con Asia, en Asia", a_a, b_a, asia)
    summary("ajustado con Asia, en Argentina y Madrid", a_a, b_a, south)
    summary("FAO-56, en Argentina y Madrid", FAO_ANGSTROM_A, FAO_ANGSTROM_B, south)
    summary("FAO-56, en Asia", FAO_ANGSTROM_A, FAO_ANGSTROM_B, asia)


def hong_kong(service: MeteoService) -> None:
    """Nubosidad y radiación de ERA5 frente a las normales del Observatorio de Hong Kong."""
    series = _daily(service, ASIA_STATIONS["Hong Kong, King's Park (HKO)"])
    _, cloud = monthly_table(series.dates, series.cloud_cover_pct, "mean")
    _, radiation = monthly_table(series.dates, series.radiation_mj_m2, "mean")
    cloud_m, radiation_m = np.nanmean(cloud, axis=0), np.nanmean(radiation, axis=0)
    measured_cloud, measured_rad = np.array(HK_CLOUD_PCT), np.array(HK_RADIATION_MJ)
    print(
        f"\nHong Kong {PERIOD[0]}-{PERIOD[1]} (HKO): "
        "nubosidad (%) y radiación global (MJ/m² por día)"
    )
    print(f"{'mes':>12}" + "".join(f"{m:>6d}" for m in range(1, 13)) + "   año")
    for label, values, fmt in (
        ("nubes medida", measured_cloud, "{:6.0f}"),
        ("nubes ERA5", cloud_m, "{:6.0f}"),
        ("rad. medida", measured_rad, "{:6.1f}"),
        ("rad. ERA5", radiation_m, "{:6.1f}"),
    ):
        print(
            f"{label:>12}"
            + "".join(fmt.format(v) for v in values)
            + "   "
            + fmt.format(values.mean())
        )
    cloud_diff = cloud_m.mean() - measured_cloud.mean()
    rad_ratio = radiation_m.mean() / measured_rad.mean() - 1
    print(
        f"\nNubosidad anual: ERA5 {cloud_m.mean():.0f} % contra "
        f"{measured_cloud.mean():.0f} % medido "
        f"({cloud_diff:+.0f} puntos); error medio absoluto mensual "
        f"{np.mean(np.abs(cloud_m - measured_cloud)):.0f} puntos."
    )
    print(
        f"Radiación anual: ERA5 {radiation_m.mean():.2f} contra {measured_rad.mean():.2f} medido "
        f"({rad_ratio * 100:+.0f} %); error medio absoluto mensual "
        f"{np.mean(np.abs(radiation_m / measured_rad - 1)) * 100:.0f} %."
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
    elif "--asia" in sys.argv:
        comparar(service, ASIA_STATIONS)
        hong_kong(service)
    else:
        comparar(service)


if __name__ == "__main__":
    main()
