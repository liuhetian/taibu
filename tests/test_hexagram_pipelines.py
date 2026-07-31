from datetime import UTC, datetime

from suanming.runtime import run_pipeline
from suanming.shared.hexagrams import TRIGRAM_BY_NAME, hexagram_from_trigrams


def test_qian_and_kun_hexagram_mapping() -> None:
    qian = TRIGRAM_BY_NAME["乾"]
    kun = TRIGRAM_BY_NAME["坤"]
    assert hexagram_from_trigrams(qian, qian).number == 1
    assert hexagram_from_trigrams(kun, kun).number == 2
    assert hexagram_from_trigrams(kun, qian).number == 11


def test_liuyao_manual_cast() -> None:
    result = run_pipeline(
        "liuyao",
        {
            "method": "manual",
            "throws": [9, 7, 7, 8, 8, 8],
            "datetime": "2026-07-30T12:00:00",
        },
        seed="ignored",
    )
    assert result.result["moving_lines"] == [1]
    assert len(result.result["lines"]) == 6
    assert result.result["primary"]["number"] != result.result["changed"]["number"]


def test_meihua_two_numbers() -> None:
    result = run_pipeline(
        "meihua",
        {
            "method": "two_numbers",
            "numbers": [1, 8],
            "datetime": "2026-07-30T12:00:00",
        },
    )
    assert result.result["primary"]["upper_trigram"]["name"] == "乾"
    assert result.result["primary"]["lower_trigram"]["name"] == "坤"
    assert result.result["moving_line"] == 3


def test_xiaoliuren_manual_numbers() -> None:
    result = run_pipeline(
        "xiaoliuren",
        {
            "lunar_month": 1,
            "lunar_day": 1,
            "hour_index": 1,
        },
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.result["result_palace"] == "大安"
    assert result.result["calendar_basis"] == "manual_lunar_numbers"

