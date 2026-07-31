from datetime import UTC, datetime

import pytest

from suanming.shared.ganzhi import four_pillars
from suanming.shared.time import gregorian_jdn, localize_datetime, solar_term_at


def test_known_julian_day_number() -> None:
    assert gregorian_jdn(2000, 1, 1) == 2451545


def test_known_jiazi_day_calibration() -> None:
    pillars = four_pillars(datetime(2000, 1, 7, 12, tzinfo=UTC))
    assert pillars.day.name == "甲子"


def test_solar_term_classification_near_summer_solstice() -> None:
    term = solar_term_at(datetime(2024, 6, 21, 12, tzinfo=UTC))
    assert term.name == "夏至"
    assert 90 <= term.longitude < 105


def test_nonexistent_dst_local_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="不存在"):
        localize_datetime(
            datetime(2026, 3, 8, 2, 30),
            "America/New_York",
        )


def test_ambiguous_dst_local_time_requires_explicit_offset() -> None:
    with pytest.raises(ValueError, match="两个可能偏移量"):
        localize_datetime(
            datetime(2026, 11, 1, 1, 30),
            "America/New_York",
        )


def test_aware_datetime_disambiguates_dst_time() -> None:
    value = datetime.fromisoformat("2026-11-01T01:30:00-05:00")
    localized = localize_datetime(value, "America/New_York")

    assert localized.isoformat() == "2026-11-01T01:30:00-05:00"
    assert localized.fold == 1
