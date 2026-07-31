from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from suanming.runtime import run_pipeline

SAMPLES = {
    "almanac": {"date": "2026-07-30"},
    "astrology": {
        "datetime": "1990-05-15T15:30:00",
        "latitude": 31.23,
        "longitude": 121.47,
    },
    "bazi": {"datetime": "1990-05-15T15:30:00"},
    "bazi_dayun": {"datetime": "1990-05-15T15:30:00", "gender": "male"},
    "bazi_pillars_resolve": {
        "year_pillar": "庚午",
        "month_pillar": "辛巳",
        "day_pillar": "庚辰",
        "hour_pillar": "甲申",
        "start_year": 1990,
        "end_year": 1990,
    },
    "compatibility": {
        "first": {"label": "甲", "datetime": "1990-05-15T15:30:00"},
        "second": {"label": "乙", "datetime": "1992-09-20T08:15:00"},
    },
    "daliuren": {"datetime": "2026-07-30T14:00:00"},
    "dream": {"dream": "我梦见在海边飞行，然后回到一座房子。", "emotions": ["平静"]},
    "face": {
        "forehead": "balanced",
        "eyebrows": "clear",
        "eyes": "bright",
        "nose": "straight",
        "mouth": "defined",
        "chin": "rounded",
    },
    "fortune": {
        "birth_datetime": "1990-05-15T15:30:00",
        "target_date": "2026-07-30",
        "periods": 3,
    },
    "guanyin_oracle": {"question": "怎样稳步推进当前项目？"},
    "liuyao": {"method": "manual", "throws": [7, 8, 7, 8, 9, 6]},
    "lvzu_oracle": {"question": "眼前的选择应怎样验证？"},
    "mbti": {
        "responses": {
            "ei01": 2,
            "ei02": 1,
            "sn01": 2,
            "sn02": 1,
            "tf01": 2,
            "tf02": 1,
            "jp01": 2,
            "jp02": 1,
        }
    },
    "meihua": {"method": "two_numbers", "numbers": [17, 29]},
    "numerology": {"birth_date": "1990-05-15", "name": "Example Name"},
    "palm": {
        "life_line": "deep",
        "head_line": "forked",
        "heart_line": "long",
        "fate_line": "clear",
    },
    "patriarch_oracle": {"question": "怎样建立可扩展的工程基础？"},
    "qimen": {"datetime": "2026-07-30T14:00:00"},
    "taiyi": {"datetime": "2026-07-30T14:00:00"},
    "tarot": {"spread": "three_card", "question": "当前项目的下一步是什么？"},
    "tianshi_oracle": {"question": "怎样保持规则与扩展的平衡？"},
    "xiaoliuren": {"lunar_month": 6, "lunar_day": 17, "hour_index": 8},
    "ziwei": {
        "lunar_year": 1990,
        "lunar_month": 4,
        "lunar_day": 21,
        "hour_branch": "申",
        "gender": "male",
    },
    "ziwei_flying_star": {
        "lunar_year": 1990,
        "lunar_month": 4,
        "lunar_day": 21,
        "hour_branch": "申",
        "gender": "male",
    },
    "ziwei_horoscope": {
        "lunar_year": 1990,
        "lunar_month": 4,
        "lunar_day": 21,
        "hour_branch": "申",
        "gender": "male",
        "target_year": 2026,
        "target_lunar_month": 6,
        "target_lunar_day": 17,
        "target_hour_branch": "未",
    },
}


@pytest.mark.parametrize("pipeline_id", sorted(SAMPLES))
def test_every_pipeline_executes_and_serializes(pipeline_id: str) -> None:
    envelope = run_pipeline(
        pipeline_id,
        SAMPLES[pipeline_id],
        seed="catalog-smoke-test",
        now=datetime(2026, 7, 30, tzinfo=UTC),
    )
    assert envelope.pipeline.id == pipeline_id
    assert envelope.result
    assert envelope.reproducibility.run_id
    assert envelope.model_dump_json()
    for asset in envelope.assets:
        assert asset.status == "available"
        assert asset.path is not None
        assert (Path(__file__).parents[1] / asset.path).is_file()


def test_content_oracle_seed_is_reproducible() -> None:
    request = {"question": "如何推进？", "draws": 3}
    first = run_pipeline("patriarch_oracle", request, seed="same")
    second = run_pipeline("patriarch_oracle", request, seed="same")
    assert first.result["draws"] == second.result["draws"]
    assert len({item["number"] for item in first.result["draws"]}) == 3
