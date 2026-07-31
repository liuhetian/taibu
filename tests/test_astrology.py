from suanming.runtime import run_pipeline


def test_astrology_positions_and_houses() -> None:
    envelope = run_pipeline(
        "astrology",
        {
            "datetime": "2000-01-01T12:00:00",
            "timezone": "UTC",
            "latitude": 31.2304,
            "longitude": 121.4737,
        },
    )
    result = envelope.result
    assert len(result["points"]) == 9
    sun = next(point for point in result["points"] if point["id"] == "sun")
    assert sun["sign"] == "摩羯座"
    assert 270 <= sun["longitude"] < 300
    assert result["ascendant"]["house"] == 1
    assert all(point["house"] is not None for point in result["points"])

