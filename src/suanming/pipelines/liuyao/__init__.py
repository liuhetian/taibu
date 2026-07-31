from __future__ import annotations

from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import BRANCH_ELEMENTS, four_pillars
from ...shared.hexagrams import (
    changed_hexagram,
    hexagram_dict,
    hexagram_from_lines,
    mutual_hexagram,
    opposite_hexagram,
    reversed_hexagram,
)
from ...shared.time import localize_datetime, timezone_of


NAJIA_BRANCHES = {
    "乾": (("子", "寅", "辰"), ("午", "申", "戌")),
    "坤": (("未", "巳", "卯"), ("丑", "亥", "酉")),
    "震": (("子", "寅", "辰"), ("午", "申", "戌")),
    "巽": (("丑", "亥", "酉"), ("未", "巳", "卯")),
    "坎": (("寅", "辰", "午"), ("申", "戌", "子")),
    "离": (("卯", "丑", "亥"), ("酉", "未", "巳")),
    "艮": (("辰", "午", "申"), ("戌", "子", "寅")),
    "兑": (("巳", "卯", "丑"), ("亥", "酉", "未")),
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


class LiuyaoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["coins", "time", "manual"] = "coins"
    question: str | None = Field(default=None, max_length=500)
    datetime: DateTime | None = None
    timezone: str = "Asia/Shanghai"
    throws: list[int] | None = Field(default=None, min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_method(self) -> "LiuyaoInput":
        timezone_of(self.timezone)
        if self.method == "manual":
            if self.throws is None or any(value not in {6, 7, 8, 9} for value in self.throws):
                raise ValueError("manual 模式需要六个 6/7/8/9 爻值。")
        return self


class LiuyaoLine(BaseModel):
    number: int
    value: int
    yin_yang: str
    moving: bool
    branch: str
    element: str
    relative: str


class LiuyaoOutput(BaseModel):
    method: str
    question: str | None
    datetime: DateTime
    day_pillar: str
    lines: list[LiuyaoLine]
    moving_lines: list[int]
    primary: dict[str, object]
    changed: dict[str, object]
    mutual: dict[str, object]
    opposite: dict[str, object]
    reversed: dict[str, object]
    method_notes: list[str]


def _relative(reference: str, other: str) -> str:
    if reference == other:
        return "兄弟"
    if GENERATES[other] == reference:
        return "父母"
    if GENERATES[reference] == other:
        return "子孙"
    if CONTROLS[reference] == other:
        return "妻财"
    return "官鬼"


def _time_throws(value: DateTime) -> list[int]:
    pillars = four_pillars(value, day_boundary="zi_hour")
    base = value.year + value.month + value.day + ((value.hour + 1) // 2)
    moving = base % 6
    lines = [
        7 if ((pillars.day.index >> index) & 1) else 8
        for index in range(6)
    ]
    lines[moving] = 9 if lines[moving] == 7 else 6
    return lines


def calculate_liuyao(request: LiuyaoInput, context: RunContext) -> LiuyaoOutput:
    effective = localize_datetime(
        request.datetime or context.effective_datetime,
        request.timezone,
    )
    if request.method == "manual":
        assert request.throws is not None
        throws = list(request.throws)
    elif request.method == "time":
        throws = _time_throws(effective)
    else:
        throws = [
            sum(context.rng.choice((2, 3)) for _ in range(3))
            for _ in range(6)
        ]

    binary = [1 if value in {7, 9} else 0 for value in throws]
    moving_lines = [index + 1 for index, value in enumerate(throws) if value in {6, 9}]
    primary = hexagram_from_lines(binary)
    changed = changed_hexagram(primary, moving_lines)
    inner_branches = NAJIA_BRANCHES[primary.lower.name][0]
    outer_branches = NAJIA_BRANCHES[primary.upper.name][1]
    branches = (*inner_branches, *outer_branches)
    reference_element = primary.upper.element
    line_models = [
        LiuyaoLine(
            number=index + 1,
            value=value,
            yin_yang="阳" if binary[index] else "阴",
            moving=value in {6, 9},
            branch=branches[index],
            element=BRANCH_ELEMENTS[branches[index]],
            relative=_relative(reference_element, BRANCH_ELEMENTS[branches[index]]),
        )
        for index, value in enumerate(throws)
    ]
    day = four_pillars(effective, day_boundary="zi_hour").day.name
    return LiuyaoOutput(
        method=request.method,
        question=request.question,
        datetime=effective,
        day_pillar=day,
        lines=line_models,
        moving_lines=moving_lines,
        primary=hexagram_dict(primary),
        changed=hexagram_dict(changed),
        mutual=hexagram_dict(mutual_hexagram(primary)),
        opposite=hexagram_dict(opposite_hexagram(primary)),
        reversed=hexagram_dict(reversed_hexagram(primary)),
        method_notes=[
            "六爻自下而上排列，6/9 为动爻，7/8 为静爻。",
            "coins 模式以结果信封中的 seed 模拟三枚钱币。",
            "纳甲地支与六亲按上下卦五行关系结构化给出。",
        ],
    )


@register_pipeline
class LiuyaoPipeline(Pipeline[LiuyaoInput, LiuyaoOutput]):
    manifest = PipelineManifest(
        id="liuyao",
        name="六爻",
        version="0.1.0",
        ruleset="three-coins-najia-v1",
        category="hexagram_oracle",
        tradition="chinese",
        mode=PipelineMode.HYBRID,
        summary="支持钱币、时间与手工六爻起卦，输出本卦、变卦、互卦、错卦、综卦与六亲。",
        asset_pack="yijing-v1",
        tags=["六十四卦", "动爻", "纳甲", "六亲"],
    )
    input_model = LiuyaoInput
    output_model = LiuyaoOutput

    def execute(self, request: LiuyaoInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(result=calculate_liuyao(request, context))

