from __future__ import annotations

from datetime import datetime as DateTime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import STEM_ELEMENTS, four_pillars, ganzhi_at, yin_yang_of_stem
from ...shared.time import localize_datetime, solar_longitude, timezone_of


class BaziDayunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime
    timezone: str = "Asia/Shanghai"
    gender: Literal["male", "female"]
    cycles: int = Field(default=8, ge=1, le=12)

    @model_validator(mode="after")
    def validate_timezone(self) -> "BaziDayunInput":
        timezone_of(self.timezone)
        return self


class DayunCycle(BaseModel):
    order: int
    pillar: str
    stem_element: str
    start_age: float
    end_age: float
    start_date: DateTime
    end_date: DateTime


class BaziDayunOutput(BaseModel):
    birth_datetime: DateTime
    gender: str
    direction: Literal["forward", "backward"]
    direction_basis: str
    days_to_boundary: float
    start_age: float
    cycles: list[DayunCycle]
    method_notes: list[str]


def calculate_dayun(request: BaziDayunInput) -> BaziDayunOutput:
    birth = localize_datetime(request.datetime, request.timezone)
    pillars = four_pillars(birth)
    year_yang = yin_yang_of_stem(pillars.year.stem) == "阳"
    forward = (request.gender == "male") == year_yang

    # The twelve "jie" month boundaries are 30° apart, beginning at 立春 315°.
    phase = (solar_longitude(birth) - 315.0) % 30.0
    degrees = (30.0 - phase) if forward else phase
    days = degrees / 0.98564736
    start_age = days / 3.0
    start_date = birth + timedelta(days=days * 120.0)

    cycles: list[DayunCycle] = []
    direction_step = 1 if forward else -1
    for order in range(1, request.cycles + 1):
        pillar = ganzhi_at(pillars.month.index + direction_step * order)
        cycle_start = start_date + timedelta(days=(order - 1) * 3652.422)
        cycle_end = start_date + timedelta(days=order * 3652.422)
        cycles.append(
            DayunCycle(
                order=order,
                pillar=pillar.name,
                stem_element=STEM_ELEMENTS[pillar.stem],
                start_age=round(start_age + (order - 1) * 10, 3),
                end_age=round(start_age + order * 10, 3),
                start_date=cycle_start,
                end_date=cycle_end,
            )
        )
    return BaziDayunOutput(
        birth_datetime=birth,
        gender=request.gender,
        direction="forward" if forward else "backward",
        direction_basis=f"{pillars.year.stem}年干为{yin_yang_of_stem(pillars.year.stem)}，{request.gender}",
        days_to_boundary=round(days, 6),
        start_age=round(start_age, 3),
        cycles=cycles,
        method_notes=[
            "阳年男、阴年女顺排；阴年男、阳年女逆排。",
            "从出生时刻量至顺逆方向的相邻节令，按三日折一年换算起运年龄。",
            "十年边界按回归年近似换算为公历时间；不同门派在虚岁与折算细节上可能不同。",
        ],
    )


@register_pipeline
class BaziDayunPipeline(Pipeline[BaziDayunInput, BaziDayunOutput]):
    manifest = PipelineManifest(
        id="bazi_dayun",
        name="八字大运",
        version="0.1.0",
        ruleset="jie-boundary-three-days-one-year-v1",
        category="fortune_cycle",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="由年干阴阳与性别确定顺逆，按节令间隔计算起运并排出十年大运。",
        asset_pack="bazi-v1",
        tags=["大运", "顺逆", "起运", "十年运"],
    )
    input_model = BaziDayunInput
    output_model = BaziDayunOutput

    def execute(self, request: BaziDayunInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(result=calculate_dayun(request))
