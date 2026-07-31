from suanming.pipelines.bazi import BaziInput, calculate_bazi
from suanming.runtime import run_pipeline


def test_bazi_reference_case() -> None:
    result = calculate_bazi(
        BaziInput.model_validate(
            {
                "datetime": "1990-05-15T15:30:00",
                "timezone": "Asia/Shanghai",
                "gender": "male",
            }
        )
    )
    assert result.four_pillars["year"].ganzhi == "庚午"
    assert result.four_pillars["month"].ganzhi == "辛巳"
    assert result.four_pillars["day"].ganzhi == "庚辰"
    assert result.four_pillars["hour"].ganzhi == "甲申"
    assert result.day_master == {"stem": "庚", "element": "金", "yin_yang": "阳"}
    assert sum(result.five_elements.values()) > 8


def test_true_solar_time_requires_longitude() -> None:
    try:
        BaziInput.model_validate(
            {
                "datetime": "1990-05-15T15:30:00",
                "true_solar_time": True,
            }
        )
    except ValueError as exc:
        assert "longitude" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("validation should fail")


def test_zi_hour_reverse_lookup_does_not_include_previous_day() -> None:
    result = run_pipeline(
        "bazi_pillars_resolve",
        {
            "year_pillar": "庚午",
            "month_pillar": "辛巳",
            "day_pillar": "庚辰",
            "hour_pillar": "丙子",
            "start_year": 1990,
            "end_year": 1990,
        },
    ).result

    candidate = result["candidates"][0]
    assert candidate["representative_datetime"].startswith("1990-05-15T00:00:00")
    assert candidate["hour_window"] == "00:00-00:59"
