from suanming.runtime import run_pipeline


def test_almanac_has_twelve_hours() -> None:
    result = run_pipeline(
        "almanac",
        {"date": "2026-07-30", "timezone": "Asia/Shanghai"},
    ).result
    assert len(result["hours"]) == 12
    assert {hour["branch"] for hour in result["hours"]} == set("子丑寅卯辰巳午未申酉戌亥")
    assert result["day_officer"].endswith("日")
