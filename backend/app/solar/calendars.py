"""Utilidades de calendario: fecha de Pascua, día de la semana y día del año
(Meeus caps. 7 y 8).

La Pascua tiene dos algoritmos: el gregoriano (desde 1583 en la práctica;
el calendario gregoriano se adoptó en 1582) y el juliano (la Pascua de las
iglesias ortodoxas, que sigue calculándose con el calendario juliano; la
fecha que da está en el calendario juliano). La fecha de Pascua devuelta
está en el calendario indicado, no convertida: la Pascua ortodoxa de 2024,
por ejemplo, es el 22 de abril del calendario juliano, que equivale al 5 de
mayo gregoriano; `julian_to_gregorian` hace esa conversión.

Las fechas se devuelven como `(año, mes, día)` y no como `datetime.date`
porque Python solo representa el calendario gregoriano proléptico.
"""

import calendar as _std_calendar
import math

from app.solar.time import calendar_from_julian_day, julian_day_from_calendar

_WEEKDAYS_ES = ("domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado")


def is_leap_year(year: int, calendar: str = "gregorian") -> bool:
    """Si `year` es bisiesto en el calendario `"gregorian"` o `"julian"`."""
    if calendar == "julian":
        return year % 4 == 0
    if calendar == "gregorian":
        return _std_calendar.isleap(year)
    raise ValueError(f"calendar inválido: {calendar!r}")


def easter(year: int, calendar: str = "gregorian") -> tuple[int, int, int]:
    """Domingo de Pascua de `year`, como `(año, mes, día)` en el calendario
    `calendar` (Meeus cap. 8).

    `"gregorian"` es la Pascua de las iglesias occidentales (válido desde
    1583); `"julian"`, la fecha en calendario juliano que usan las iglesias
    ortodoxas (válido desde el año 326, concilio de Nicea). Con `"auto"`
    se usa el calendario vigente en ese año: juliano hasta 1582, gregoriano
    desde 1583.
    """
    if calendar == "auto":
        calendar = "julian" if year <= 1582 else "gregorian"

    if calendar == "julian":
        a, b, c = year % 4, year % 7, year % 19
        d = (19 * c + 15) % 30
        e = (2 * a + 4 * b - d + 34) % 7
        month, day = divmod(d + e + 114, 31)
        return year, month, day + 1

    if calendar == "gregorian":
        a = year % 19
        b, c = divmod(year, 100)
        d, e = divmod(b, 4)
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = divmod(c, 4)
        ell = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * ell) // 451
        month, day = divmod(h + ell - 7 * m + 114, 31)
        return year, month, day + 1

    raise ValueError(f"calendar inválido: {calendar!r}")


def julian_to_gregorian(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convierte una fecha del calendario juliano al gregoriano (misma fecha
    astronómica; el calendario gregoriano se extiende hacia atrás de forma
    proléptica)."""
    jd = julian_day_from_calendar(year, month, day, "julian")
    y, m, d, _ = calendar_from_julian_day(jd, "gregorian")
    return y, m, int(math.floor(d))


def weekday(year: int, month: int, day: int, calendar: str = "auto") -> int:
    """Día de la semana de una fecha (Meeus cap. 7): 0 = domingo, 1 = lunes,
    ..., 6 = sábado."""
    jd = julian_day_from_calendar(year, month, day, calendar)
    return int(math.floor(jd + 1.5)) % 7


def weekday_name(year: int, month: int, day: int, calendar: str = "auto") -> str:
    """Nombre del día de la semana, en español."""
    return _WEEKDAYS_ES[weekday(year, month, day, calendar)]


def day_of_year(year: int, month: int, day: int, calendar: str = "gregorian") -> int:
    """Número de día dentro del año (1 de enero = 1), Meeus cap. 7."""
    k = 1 if is_leap_year(year, calendar) else 2
    return (275 * month) // 9 - k * ((month + 9) // 12) + day - 30


def date_from_day_of_year(year: int, n: int, calendar: str = "gregorian") -> tuple[int, int, int]:
    """Fecha `(año, mes, día)` del día número `n` del año (Meeus cap. 7)."""
    leap = is_leap_year(year, calendar)
    if not 1 <= n <= (366 if leap else 365):
        raise ValueError("n fuera del rango del año")
    k = 1 if leap else 2
    month = int(9 * (k + n) / 275 + 0.98) if n >= 32 else 1
    day = n - (275 * month) // 9 + k * ((month + 9) // 12) + 30
    return year, month, day
