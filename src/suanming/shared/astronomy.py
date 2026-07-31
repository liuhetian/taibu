from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from .time import julian_day


def _normalize(degrees: float) -> float:
    return degrees % 360.0


def _signed_delta(end: float, start: float) -> float:
    return (end - start + 180.0) % 360.0 - 180.0


def _sin(degrees: float) -> float:
    return math.sin(math.radians(degrees))


def _cos(degrees: float) -> float:
    return math.cos(math.radians(degrees))


def _atan2(y: float, x: float) -> float:
    return math.degrees(math.atan2(y, x))


def _eccentric_anomaly(mean_anomaly: float, eccentricity: float) -> float:
    mean_radians = math.radians(mean_anomaly)
    estimate = mean_radians + eccentricity * math.sin(mean_radians) * (
        1.0 + eccentricity * math.cos(mean_radians)
    )
    for _ in range(8):
        estimate -= (estimate - eccentricity * math.sin(estimate) - mean_radians) / (
            1.0 - eccentricity * math.cos(estimate)
        )
    return estimate


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    node: float
    inclination: float
    perihelion: float
    distance: float
    eccentricity: float
    mean_anomaly: float


@dataclass(frozen=True, slots=True)
class EclipticPosition:
    longitude: float
    latitude: float
    distance: float


def _days(value: datetime) -> float:
    return julian_day(value) - 2451543.5


def _sun_coordinates(days: float) -> tuple[float, float, float, float]:
    perihelion = 282.9404 + 4.70935e-5 * days
    eccentricity = 0.016709 - 1.151e-9 * days
    mean_anomaly = _normalize(356.0470 + 0.9856002585 * days)
    eccentric = _eccentric_anomaly(mean_anomaly, eccentricity)
    xv = math.cos(eccentric) - eccentricity
    yv = math.sqrt(1.0 - eccentricity**2) * math.sin(eccentric)
    true_anomaly = _atan2(yv, xv)
    distance = math.hypot(xv, yv)
    longitude = _normalize(true_anomaly + perihelion)
    return distance * _cos(longitude), distance * _sin(longitude), distance, longitude


def _elements(body: str, days: float) -> OrbitalElements:
    values = {
        "mercury": (
            48.3313 + 3.24587e-5 * days,
            7.0047 + 5.0e-8 * days,
            29.1241 + 1.01444e-5 * days,
            0.387098,
            0.205635 + 5.59e-10 * days,
            168.6562 + 4.0923344368 * days,
        ),
        "venus": (
            76.6799 + 2.46590e-5 * days,
            3.3946 + 2.75e-8 * days,
            54.8910 + 1.38374e-5 * days,
            0.723330,
            0.006773 - 1.302e-9 * days,
            48.0052 + 1.6021302244 * days,
        ),
        "mars": (
            49.5574 + 2.11081e-5 * days,
            1.8497 - 1.78e-8 * days,
            286.5016 + 2.92961e-5 * days,
            1.523688,
            0.093405 + 2.516e-9 * days,
            18.6021 + 0.5240207766 * days,
        ),
        "jupiter": (
            100.4542 + 2.76854e-5 * days,
            1.3030 - 1.557e-7 * days,
            273.8777 + 1.64505e-5 * days,
            5.20256,
            0.048498 + 4.469e-9 * days,
            19.8950 + 0.0830853001 * days,
        ),
        "saturn": (
            113.6634 + 2.38980e-5 * days,
            2.4886 - 1.081e-7 * days,
            339.3939 + 2.97661e-5 * days,
            9.55475,
            0.055546 - 9.499e-9 * days,
            316.9670 + 0.0334442282 * days,
        ),
        "uranus": (
            74.0005 + 1.3978e-5 * days,
            0.7733 + 1.9e-8 * days,
            96.6612 + 3.0565e-5 * days,
            19.18171 - 1.55e-8 * days,
            0.047318 + 7.45e-9 * days,
            142.5905 + 0.011725806 * days,
        ),
        "neptune": (
            131.7806 + 3.0173e-5 * days,
            1.7700 - 2.55e-7 * days,
            272.8461 - 6.027e-6 * days,
            30.05826 + 3.313e-8 * days,
            0.008606 + 2.15e-9 * days,
            260.2471 + 0.005995147 * days,
        ),
    }
    return OrbitalElements(*values[body])


def _heliocentric(elements: OrbitalElements) -> tuple[float, float, float, float]:
    eccentric = _eccentric_anomaly(
        _normalize(elements.mean_anomaly),
        elements.eccentricity,
    )
    xv = elements.distance * (math.cos(eccentric) - elements.eccentricity)
    yv = elements.distance * math.sqrt(1.0 - elements.eccentricity**2) * math.sin(eccentric)
    true_anomaly = _atan2(yv, xv)
    radius = math.hypot(xv, yv)
    argument = true_anomaly + elements.perihelion
    xh = radius * (
        _cos(elements.node) * _cos(argument)
        - _sin(elements.node) * _sin(argument) * _cos(elements.inclination)
    )
    yh = radius * (
        _sin(elements.node) * _cos(argument)
        + _cos(elements.node) * _sin(argument) * _cos(elements.inclination)
    )
    zh = radius * _sin(argument) * _sin(elements.inclination)
    return xh, yh, zh, radius


def _moon_position(days: float) -> EclipticPosition:
    elements = OrbitalElements(
        node=125.1228 - 0.0529538083 * days,
        inclination=5.1454,
        perihelion=318.0634 + 0.1643573223 * days,
        distance=60.2666,
        eccentricity=0.054900,
        mean_anomaly=115.3654 + 13.0649929509 * days,
    )
    x, y, z, radius = _heliocentric(elements)
    longitude = _normalize(_atan2(y, x))
    latitude = _atan2(z, math.hypot(x, y))
    return EclipticPosition(longitude, latitude, radius)


def body_position(body: str, value: datetime) -> EclipticPosition:
    days = _days(value)
    sun_x, sun_y, sun_distance, sun_longitude = _sun_coordinates(days)
    if body == "sun":
        return EclipticPosition(sun_longitude, 0.0, sun_distance)
    if body == "moon":
        return _moon_position(days)

    xh, yh, zh, radius = _heliocentric(_elements(body, days))
    xg = xh + sun_x
    yg = yh + sun_y
    zg = zh
    return EclipticPosition(
        _normalize(_atan2(yg, xg)),
        _atan2(zg, math.hypot(xg, yg)),
        radius,
    )


BODY_ORDER = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
)


def planetary_positions(value: datetime) -> dict[str, EclipticPosition]:
    return {body: body_position(body, value) for body in BODY_ORDER}


def is_retrograde(body: str, value: datetime) -> bool:
    if body in {"sun", "moon"}:
        return False
    previous = body_position(body, value - timedelta(hours=12)).longitude
    following = body_position(body, value + timedelta(hours=12)).longitude
    return _signed_delta(following, previous) < 0


def local_sidereal_degrees(value: datetime, longitude: float) -> float:
    jd = julian_day(value)
    centuries = (jd - 2451545.0) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * centuries**2
        - centuries**3 / 38710000.0
    )
    return _normalize(gmst + longitude)


def ascendant_longitude(value: datetime, latitude: float, longitude: float) -> float:
    sidereal = math.radians(local_sidereal_degrees(value, longitude))
    obliquity = math.radians(23.439291)
    latitude_radians = math.radians(latitude)
    result = math.degrees(
        math.atan2(
            -math.cos(sidereal),
            math.sin(sidereal) * math.cos(obliquity)
            + math.tan(latitude_radians) * math.sin(obliquity),
        )
    )
    return _normalize(result + 180.0)
