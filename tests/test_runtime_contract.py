from datetime import UTC, datetime

from suanming.runtime import describe_pipelines, pipeline_schema, run_pipeline


EXPECTED_PIPELINES = {
    "almanac",
    "astrology",
    "bazi",
    "bazi_dayun",
    "bazi_pillars_resolve",
    "compatibility",
    "daliuren",
    "dream",
    "face",
    "fortune",
    "guanyin_oracle",
    "liuyao",
    "lvzu_oracle",
    "mbti",
    "meihua",
    "numerology",
    "palm",
    "patriarch_oracle",
    "qimen",
    "taiyi",
    "tarot",
    "tianshi_oracle",
    "xiaoliuren",
    "ziwei",
    "ziwei_flying_star",
    "ziwei_horoscope",
}


def test_complete_pipeline_catalog_is_discovered() -> None:
    pipeline_ids = {item["id"] for item in describe_pipelines()}
    assert pipeline_ids == EXPECTED_PIPELINES


def test_every_pipeline_exposes_json_schemas() -> None:
    for pipeline_id in EXPECTED_PIPELINES:
        schemas = pipeline_schema(pipeline_id, "both")
        assert schemas["input"]["type"] == "object"
        assert schemas["output"]["type"] == "object"
        assert schemas["manifest"]["id"] == pipeline_id


def test_deterministic_pipeline_has_stable_envelope() -> None:
    request = {
        "datetime": "1990-05-15T15:30:00",
        "timezone": "Asia/Shanghai",
    }
    first = run_pipeline(
        "bazi",
        request,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = run_pipeline(
        "bazi",
        request,
        now=datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert first.result == second.result
    assert first.reproducibility.run_id == second.reproducibility.run_id
    assert first.reproducibility.seed == "deterministic"


def test_envelope_contains_only_json_serializable_values() -> None:
    envelope = run_pipeline(
        "tarot",
        {"spread": "single"},
        seed="json-contract",
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    encoded = envelope.model_dump_json()
    assert '"schema_version":"1.0"' in encoded
