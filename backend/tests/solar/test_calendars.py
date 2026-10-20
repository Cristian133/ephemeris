import pytest

from app.solar.calendars import (
    date_from_day_of_year,
    day_of_year,
    easter,
    is_leap_year,
    julian_to_gregorian,
    weekday,
    weekday_name,
)


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (1991, (1991, 3, 31)),  # Meeus, ejemplo 8.a
        (1992, (1992, 4, 19)),
        (1993, (1993, 4, 11)),
        (1954, (1954, 4, 18)),
        (2000, (2000, 4, 23)),
        (1818, (1818, 3, 22)),  # fecha más temprana posible
        (2038, (2038, 4, 25)),  # fecha más tardía posible
        (2024, (2024, 3, 31)),
        (2025, (2025, 4, 20)),
        (2026, (2026, 4, 5)),
        (2027, (2027, 3, 28)),
    ],
)
def test_gregorian_easter(year: int, expected: tuple[int, int, int]) -> None:
    assert easter(year) == expected
    assert easter(year, "auto") == expected


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (179, (179, 4, 12)),  # Meeus, ejemplo 8.b
        (711, (711, 4, 12)),
        (1243, (1243, 4, 12)),
    ],
)
def test_julian_easter_historical_examples(year: int, expected: tuple[int, int, int]) -> None:
    assert easter(year, "julian") == expected
    assert easter(year, "auto") == expected  # antes de 1583, "auto" usa el juliano


@pytest.mark.parametrize(
    ("year", "gregorian_equivalent"),
    [(2024, (2024, 5, 5)), (2025, (2025, 4, 20)), (2023, (2023, 4, 16))],
)
def test_orthodox_easter_converted_to_gregorian(
    year: int, gregorian_equivalent: tuple[int, int, int]
) -> None:
    julian_date = easter(year, "julian")
    assert julian_to_gregorian(*julian_date) == gregorian_equivalent


def test_easter_is_always_a_sunday_between_march_22_and_april_25() -> None:
    for year in range(1583, 4000):
        y, month, day = easter(year)
        assert weekday(y, month, day) == 0, year
        assert (3, 22) <= (month, day) <= (4, 25), year


def test_julian_easter_is_always_a_sunday() -> None:
    for year in range(326, 1583):
        y, month, day = easter(year, "julian")
        assert weekday(y, month, day, "julian") == 0, year


def test_easter_rejects_unknown_calendar() -> None:
    with pytest.raises(ValueError):
        easter(2024, "maya")


@pytest.mark.parametrize(
    ("date", "calendar", "expected"),
    [
        ((1954, 6, 30), "auto", 3),  # Meeus, ejemplo 7.e: miércoles
        ((2000, 1, 1), "auto", 6),  # sábado
        ((2024, 3, 31), "auto", 0),  # domingo de Pascua
        ((1582, 10, 4), "auto", 4),  # jueves; el día siguiente fue el viernes 15
        ((1582, 10, 15), "auto", 5),
    ],
)
def test_weekday(date: tuple[int, int, int], calendar: str, expected: int) -> None:
    assert weekday(*date, calendar) == expected


def test_weekday_name_is_in_spanish() -> None:
    assert weekday_name(1954, 6, 30) == "miércoles"


@pytest.mark.parametrize(
    ("year", "month", "day", "n"),
    [
        (1978, 11, 14, 318),  # Meeus, ejemplo 7.f
        (1988, 4, 22, 113),
        (2023, 12, 31, 365),
        (2024, 12, 31, 366),
        (2024, 3, 1, 61),
    ],
)
def test_day_of_year_roundtrip(year: int, month: int, day: int, n: int) -> None:
    assert day_of_year(year, month, day) == n
    assert date_from_day_of_year(year, n) == (year, month, day)


def test_day_of_year_roundtrip_over_whole_years() -> None:
    for year in (1900, 2000, 2023, 2024):
        days = 366 if is_leap_year(year) else 365
        for n in range(1, days + 1):
            assert day_of_year(*date_from_day_of_year(year, n)) == n


def test_date_from_day_of_year_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        date_from_day_of_year(2023, 366)
    with pytest.raises(ValueError):
        date_from_day_of_year(2023, 0)


def test_leap_years() -> None:
    assert is_leap_year(2000) and not is_leap_year(1900) and is_leap_year(2024)
    assert is_leap_year(1900, "julian")
    with pytest.raises(ValueError):
        is_leap_year(2000, "maya")
