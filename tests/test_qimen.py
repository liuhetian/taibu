from suanming.pipelines.qimen import QimenInput, calculate_qimen


def test_qimen_has_complete_nine_palaces() -> None:
    result = calculate_qimen(
        QimenInput.model_validate(
            {
                "datetime": "2026-07-30T14:00:00",
                "timezone": "Asia/Shanghai",
                "question": "项目推进",
            }
        )
    )
    assert result.dun == "阴遁"
    assert result.solar_term == "大暑"
    assert {palace.palace for palace in result.palaces} == set(range(1, 10))
    assert len({palace.earth_stem for palace in result.palaces}) == 9
    assert len({palace.star for palace in result.palaces}) == 9
    assert len({palace.door for palace in result.palaces}) == 9

