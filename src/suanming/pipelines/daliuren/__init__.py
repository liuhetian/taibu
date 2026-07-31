from __future__ import annotations

from datetime import datetime as DateTime

from pydantic import BaseModel, ConfigDict, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import (
    BRANCH_ELEMENTS,
    CONTROLS,
    EARTHLY_BRANCHES,
    HIDDEN_STEMS,
    STEM_ELEMENTS,
    four_pillars,
)
from ...shared.time import localize_datetime, solar_longitude

STEM_LODGING = {
    "甲": "寅",
    "乙": "辰",
    "丙": "巳",
    "丁": "未",
    "戊": "巳",
    "己": "未",
    "庚": "申",
    "辛": "戌",
    "壬": "亥",
    "癸": "丑",
}
HEAVENLY_GENERALS = (
    "贵人",
    "螣蛇",
    "朱雀",
    "六合",
    "勾陈",
    "青龙",
    "天空",
    "白虎",
    "太常",
    "玄武",
    "太阴",
    "天后",
)
NOBLEMAN = {
    "甲": ("丑", "未"),
    "戊": ("丑", "未"),
    "庚": ("丑", "未"),
    "乙": ("子", "申"),
    "己": ("子", "申"),
    "丙": ("亥", "酉"),
    "丁": ("亥", "酉"),
    "壬": ("卯", "巳"),
    "癸": ("卯", "巳"),
    "辛": ("午", "寅"),
}


class DaliurenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime
    timezone: str = "Asia/Shanghai"

    @model_validator(mode="after")
    def validate_timezone(self) -> DaliurenInput:
        localize_datetime(self.datetime, self.timezone)
        return self


class PlatePosition(BaseModel):
    earth_branch: str
    heaven_branch: str
    heavenly_general: str


class Lesson(BaseModel):
    order: int
    lower: str
    lower_element: str
    upper: str
    upper_element: str
    relation: str


class Transmission(BaseModel):
    stage: str
    branch: str
    element: str
    hidden_stems: list[str]


class DaliurenOutput(BaseModel):
    datetime: DateTime
    day_pillar: str
    hour_pillar: str
    month_general: str
    earth_heaven_plate: list[PlatePosition]
    four_lessons: list[Lesson]
    lesson_type: str
    three_transmissions: list[Transmission]
    nobleman: str
    method_notes: list[str]


def _month_general(value: DateTime) -> str:
    sector = int(((solar_longitude(value) - 330.0) % 360.0) // 30.0)
    return EARTHLY_BRANCHES[(11 - sector) % 12]


def _relation(lower_element: str, upper_element: str) -> str:
    if lower_element == upper_element:
        return "比和"
    if CONTROLS[lower_element] == upper_element:
        return "下贼上"
    if CONTROLS[upper_element] == lower_element:
        return "上克下"
    return "相生"


def calculate_daliuren(request: DaliurenInput) -> DaliurenOutput:
    effective = localize_datetime(request.datetime, request.timezone)
    pillars = four_pillars(effective, day_boundary="zi_hour")
    day_stem = pillars.day.stem
    day_branch = pillars.day.branch
    hour_branch = pillars.hour.branch
    general = _month_general(effective)
    general_index = EARTHLY_BRANCHES.index(general)
    hour_index = EARTHLY_BRANCHES.index(hour_branch)
    shift = general_index - hour_index

    def upper(branch: str) -> str:
        return EARTHLY_BRANCHES[(EARTHLY_BRANCHES.index(branch) + shift) % 12]

    daytime = 6 <= effective.hour < 18
    nobleman = NOBLEMAN[day_stem][0 if daytime else 1]
    noble_index = EARTHLY_BRANCHES.index(nobleman)
    general_forward = nobleman in {"亥", "子", "丑", "寅", "卯", "辰"}
    general_by_heaven: dict[str, str] = {}
    for offset, deity in enumerate(HEAVENLY_GENERALS):
        index = noble_index + (offset if general_forward else -offset)
        general_by_heaven[EARTHLY_BRANCHES[index % 12]] = deity

    plate = [
        PlatePosition(
            earth_branch=earth,
            heaven_branch=upper(earth),
            heavenly_general=general_by_heaven[upper(earth)],
        )
        for earth in EARTHLY_BRANCHES
    ]

    lodging = STEM_LODGING[day_stem]
    lesson_pairs = [
        (day_stem, STEM_ELEMENTS[day_stem], upper(lodging)),
        (upper(lodging), BRANCH_ELEMENTS[upper(lodging)], upper(upper(lodging))),
        (day_branch, BRANCH_ELEMENTS[day_branch], upper(day_branch)),
        (upper(day_branch), BRANCH_ELEMENTS[upper(day_branch)], upper(upper(day_branch))),
    ]
    lessons = [
        Lesson(
            order=index + 1,
            lower=lower,
            lower_element=lower_element,
            upper=top,
            upper_element=BRANCH_ELEMENTS[top],
            relation=_relation(lower_element, BRANCH_ELEMENTS[top]),
        )
        for index, (lower, lower_element, top) in enumerate(lesson_pairs)
    ]

    conflict_lessons = [item for item in lessons if item.relation in {"下贼上", "上克下"}]
    if shift % 12 == 0:
        lesson_type = "伏吟"
        initial = day_branch
    elif shift % 12 == 6:
        lesson_type = "返吟"
        initial = lessons[2].upper
    elif len(conflict_lessons) == 1:
        lesson_type = "贼克"
        initial = conflict_lessons[0].upper
    elif len(conflict_lessons) > 1:
        same_polarity = [
            item
            for item in conflict_lessons
            if EARTHLY_BRANCHES.index(item.upper) % 2 == EARTHLY_BRANCHES.index(day_branch) % 2
        ]
        lesson_type = "比用" if same_polarity else "涉害"
        initial = (same_polarity or conflict_lessons)[0].upper
    else:
        lesson_type = "昴星"
        initial = upper("酉") if daytime else upper(day_branch)

    middle = upper(initial)
    final = upper(middle)
    transmissions = [
        Transmission(
            stage=stage,
            branch=branch,
            element=BRANCH_ELEMENTS[branch],
            hidden_stems=list(HIDDEN_STEMS[branch]),
        )
        for stage, branch in (("初传", initial), ("中传", middle), ("末传", final))
    ]
    return DaliurenOutput(
        datetime=effective,
        day_pillar=pillars.day.name,
        hour_pillar=pillars.hour.name,
        month_general=general,
        earth_heaven_plate=plate,
        four_lessons=lessons,
        lesson_type=lesson_type,
        three_transmissions=transmissions,
        nobleman=nobleman,
        method_notes=[
            "月将按太阳黄经每三十度换将，月将加占时布天盘。",
            "四课由日干寄宫与日支分别取两层上神。",
            "三传依次检查伏吟、返吟、贼克、比用/涉害与昴星基础路径。",
            "本版本提供核心天地盘、四课三传；复杂涉害深浅、别责、八专与神煞将以独立规则版本扩展。",
        ],
    )


@register_pipeline
class DaliurenPipeline(Pipeline[DaliurenInput, DaliurenOutput]):
    manifest = PipelineManifest(
        id="daliuren",
        name="大六壬",
        version="0.1.0",
        ruleset="month-general-four-lessons-v1",
        category="time_divination",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="由月将加时建立天地盘，计算四课、基础课体、三传与十二天将。",
        asset_pack="daliuren-v1",
        tags=["天地盘", "四课", "三传", "十二天将"],
    )
    input_model = DaliurenInput
    output_model = DaliurenOutput

    def execute(self, request: DaliurenInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_daliuren(request),
            warnings=["大六壬取法分支繁多；请以 ruleset 字段识别当前基础课体版本。"],
        )
