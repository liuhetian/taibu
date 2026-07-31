from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SOLAR_TERMS: tuple[tuple[str, float], ...] = (
    ("立春", 315.0),
    ("雨水", 330.0),
    ("惊蛰", 345.0),
    ("春分", 0.0),
    ("清明", 15.0),
    ("谷雨", 30.0),
    ("立夏", 45.0),
    ("小满", 60.0),
    ("芒种", 75.0),
    ("夏至", 90.0),
    ("小暑", 105.0),
    ("大暑", 120.0),
    ("立秋", 135.0),
    ("处暑", 150.0),
    ("白露", 165.0),
    ("秋分", 180.0),
    ("寒露", 195.0),
    ("霜降", 210.0),
    ("立冬", 225.0),
    ("小雪", 240.0),
    ("大雪", 255.0),
    ("冬至", 270.0),
    ("小寒", 285.0),
    ("大寒", 300.0),
)


@dataclass(frozen=True, slots=True)
class SolarTerm:
    index: int
    name: str
    longitude: float
    phase_degrees: float
    approximate_start: datetime


def timezone_of(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"未知时区：{name}") from exc


def localize_datetime(value: datetime, timezone_name: str) -> datetime:
    timezone = timezone_of(timezone_name)
    if value.tzinfo is not None:
        return value.astimezone(timezone)

    candidates = (
        value.replace(tzinfo=timezone, fold=0),
        value.replace(tzinfo=timezone, fold=1),
    )
    valid = [
        candidate
        for candidate in candidates
        if candidate.astimezone(UTC).astimezone(timezone).replace(tzinfo=None) == value
    ]
    if not valid:
        raise ValueError(f"{value.isoformat()} 在时区 {timezone_name} 中是不存在的当地时间。")
    if len(valid) == 2 and valid[0].utcoffset() != valid[1].utcoffset():
        raise ValueError(
            f"{value.isoformat()} 在时区 {timezone_name} 中存在两个可能偏移量；"
            "请在 datetime 中提供明确的 UTC 偏移量。"
        )
    return valid[0]


def julian_day(value: datetime) -> float:
    """Return the astronomical Julian Day for an aware datetime."""

    utc_value = value.astimezone(UTC)
    year = utc_value.year
    month = utc_value.month
    day_fraction = (
        utc_value.day
        + (
            utc_value.hour
            + utc_value.minute / 60
            + utc_value.second / 3600
            + utc_value.microsecond / 3_600_000_000
        )
        / 24
    )
    if month <= 2:
        year -= 1
        month += 12
    century = math.floor(year / 100)
    correction = 2 - century + math.floor(century / 4)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day_fraction
        + correction
        - 1524.5
    )


def gregorian_jdn(year: int, month: int, day: int) -> int:
    """Gregorian calendar date to integer Julian Day Number."""

    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def solar_longitude(value: datetime) -> float:
    """Approximate apparent geocentric solar longitude in degrees.

    The compact Meeus/NOAA series is sufficient for solar-term classification
    while keeping the runtime independent of ephemeris services.
    """

    centuries = (julian_day(value) - 2451545.0) / 36525.0
    mean_longitude = (280.46646 + centuries * (36000.76983 + 0.0003032 * centuries)) % 360
    mean_anomaly = math.radians(
        (357.52911 + centuries * (35999.05029 - 0.0001537 * centuries)) % 360
    )
    center = (
        (1.914602 - centuries * (0.004817 + 0.000014 * centuries)) * math.sin(mean_anomaly)
        + (0.019993 - 0.000101 * centuries) * math.sin(2 * mean_anomaly)
        + 0.000289 * math.sin(3 * mean_anomaly)
    )
    true_longitude = mean_longitude + center
    omega = math.radians(125.04 - 1934.136 * centuries)
    apparent = true_longitude - 0.00569 - 0.00478 * math.sin(omega)
    return apparent % 360


def _signed_angle(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def solar_term_at(value: datetime) -> SolarTerm:
    longitude = solar_longitude(value)
    phase = (longitude - 315.0) % 360.0
    index = int(phase // 15.0)
    name, target = SOLAR_TERMS[index]
    phase_degrees = phase % 15.0

    guess = value - timedelta(days=phase_degrees / 0.98564736)
    for _ in range(5):
        error = _signed_angle(solar_longitude(guess) - target)
        guess -= timedelta(days=error / 0.98564736)

    return SolarTerm(
        index=index,
        name=name,
        longitude=round(longitude, 8),
        phase_degrees=round(phase_degrees, 8),
        approximate_start=guess,
    )


def equation_of_time_minutes(value: datetime) -> float:
    local = value
    day_of_year = local.timetuple().tm_yday
    fractional_hour = local.hour + local.minute / 60 + local.second / 3600
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (fractional_hour - 12) / 24)
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def true_solar_datetime(value: datetime, longitude: float) -> tuple[datetime, float]:
    timezone = value.tzinfo
    if timezone is not None:
        winter = value.replace(month=1, day=1, hour=12, minute=0, second=0)
        summer = value.replace(month=7, day=1, hour=12, minute=0, second=0)
        offsets: list[float] = []
        for item in (winter, summer):
            offset = item.utcoffset()
            if offset is not None:
                offsets.append(offset.total_seconds() / 3600)
        offset_hours = min(offsets) if offsets else 0.0
    else:
        offset_hours = 0.0
    standard_meridian = offset_hours * 15.0
    correction = 4.0 * (longitude - standard_meridian) + equation_of_time_minutes(value)
    return value + timedelta(minutes=correction), correction
