from datetime import UTC, datetime

from suanming.shared.ganzhi import four_pillars
from suanming.shared.time import gregorian_jdn, solar_term_at


def test_known_julian_day_number() -> None:
    assert gregorian_jdn(2000, 1, 1) == 2451545


def test_known_jiazi_day_calibration() -> None:
    pillars = four_pillars(datetime(2000, 1, 7, 12, tzinfo=UTC))
    assert pillars.day.name == "甲子"


def test_solar_term_classification_near_summer_solstice() -> None:
    term = solar_term_at(datetime(2024, 6, 21, 12, tzinfo=UTC))
    assert term.name == "夏至"
    assert 90 <= term.longitude < 105

