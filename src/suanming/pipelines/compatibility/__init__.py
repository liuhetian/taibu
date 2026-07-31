from __future__ import annotations

from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import (
    CONTROLS,
    GENERATES,
    SIX_CLASHES,
    SIX_COMBINATIONS,
    SIX_HARMS,
    STEM_ELEMENTS,
    FourPillars,
    five_element_statistics,
    four_pillars,
)
from ...shared.time import localize_datetime


class PersonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    datetime: DateTime
    timezone: str = "Asia/Shanghai"

    @model_validator(mode="after")
    def validate_timezone(self) -> PersonInput:
        localize_datetime(self.datetime, self.timezone)
        return self


class CompatibilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first: PersonInput
    second: PersonInput
    relationship: Literal["partner", "business", "family", "friendship"] = "partner"


class CompatibilityFactor(BaseModel):
    id: str
    label: str
    score: float
    maximum: float
    evidence: list[str]


class CompatibilityOutput(BaseModel):
    relationship: str
    first_chart: dict[str, object]
    second_chart: dict[str, object]
    total_score: float
    factors: list[CompatibilityFactor]
    supportive_patterns: list[str]
    tension_patterns: list[str]
    method_notes: list[str]


def _chart(person: PersonInput) -> tuple[DateTime, FourPillars, dict[str, float]]:
    effective = localize_datetime(person.datetime, person.timezone)
    pillars = four_pillars(effective)
    return effective, pillars, five_element_statistics(pillars)


def calculate_compatibility(request: CompatibilityInput) -> CompatibilityOutput:
    first_time, first, first_elements = _chart(request.first)
    second_time, second, second_elements = _chart(request.second)

    first_day_element = STEM_ELEMENTS[first.day.stem]
    second_day_element = STEM_ELEMENTS[second.day.stem]
    if first_day_element == second_day_element:
        day_score, day_evidence = 17.0, ["双方日主同五行，节奏相近"]
    elif (
        GENERATES[first_day_element] == second_day_element
        or GENERATES[second_day_element] == first_day_element
    ):
        day_score, day_evidence = 20.0, ["双方日主形成相生"]
    elif (
        CONTROLS[first_day_element] == second_day_element
        or CONTROLS[second_day_element] == first_day_element
    ):
        day_score, day_evidence = 10.0, ["双方日主形成相克，需重视边界与权责"]
    else:
        day_score, day_evidence = 14.0, ["双方日主关系中性"]

    supportive: list[str] = []
    tensions: list[str] = []
    branch_points = 12.0
    labels = ("年支", "月支", "日支", "时支")
    first_branches = (first.year.branch, first.month.branch, first.day.branch, first.hour.branch)
    second_branches = (
        second.year.branch,
        second.month.branch,
        second.day.branch,
        second.hour.branch,
    )
    for label, left, right in zip(labels, first_branches, second_branches, strict=True):
        pair = frozenset((left, right))
        if pair in SIX_COMBINATIONS:
            branch_points += 3
            supportive.append(f"{label}{left}{right}六合")
        if pair in SIX_CLASHES:
            branch_points -= 3
            tensions.append(f"{label}{left}{right}六冲")
        if pair in SIX_HARMS:
            branch_points -= 2
            tensions.append(f"{label}{left}{right}六害")
    branch_points = max(0.0, min(25.0, branch_points))

    differences = [
        abs(first_elements[element] - second_elements[element])
        for element in ("木", "火", "土", "金", "水")
    ]
    balance_score = max(0.0, 25.0 - sum(differences) * 1.25)
    complement_evidence = [
        f"{element}:{first_elements[element]}/{second_elements[element]}"
        for element in ("木", "火", "土", "金", "水")
    ]

    zodiac_pair = frozenset((first.year.branch, second.year.branch))
    zodiac_score = 15.0
    zodiac_evidence = [f"年支为{first.year.branch}与{second.year.branch}"]
    if zodiac_pair in SIX_COMBINATIONS:
        zodiac_score = 20.0
        zodiac_evidence.append("年支六合")
    elif zodiac_pair in SIX_CLASHES:
        zodiac_score = 8.0
        zodiac_evidence.append("年支六冲")
    elif zodiac_pair in SIX_HARMS:
        zodiac_score = 10.0
        zodiac_evidence.append("年支六害")

    factors = [
        CompatibilityFactor(
            id="day_master",
            label="日主五行",
            score=day_score,
            maximum=25,
            evidence=day_evidence,
        ),
        CompatibilityFactor(
            id="branch_relations",
            label="四柱地支互动",
            score=round(branch_points, 2),
            maximum=25,
            evidence=supportive + tensions or ["未见直接六合、六冲或六害"],
        ),
        CompatibilityFactor(
            id="element_balance",
            label="五行结构差异",
            score=round(balance_score, 2),
            maximum=25,
            evidence=complement_evidence,
        ),
        CompatibilityFactor(
            id="year_branch",
            label="年支关系",
            score=zodiac_score,
            maximum=25,
            evidence=zodiac_evidence,
        ),
    ]
    total = round(sum(item.score for item in factors), 2)
    return CompatibilityOutput(
        relationship=request.relationship,
        first_chart={
            "label": request.first.label,
            "datetime": first_time.isoformat(),
            "pillars": [first.year.name, first.month.name, first.day.name, first.hour.name],
            "day_master": first.day.stem,
            "five_elements": first_elements,
        },
        second_chart={
            "label": request.second.label,
            "datetime": second_time.isoformat(),
            "pillars": [second.year.name, second.month.name, second.day.name, second.hour.name],
            "day_master": second.day.stem,
            "five_elements": second_elements,
        },
        total_score=total,
        factors=factors,
        supportive_patterns=supportive,
        tension_patterns=tensions,
        method_notes=[
            "分数是规则透明的结构摘要，不代表关系质量或现实结果。",
            "仅比较四柱五行、同位地支与年支关系；沟通、价值观和处境应由现实信息判断。",
        ],
    )


@register_pipeline
class CompatibilityPipeline(Pipeline[CompatibilityInput, CompatibilityOutput]):
    manifest = PipelineManifest(
        id="compatibility",
        name="关系合盘",
        version="0.1.0",
        ruleset="bazi-structural-compatibility-v1",
        category="relationship",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="比较两组四柱的日主、地支关系与五行结构，输出可解释的分项结果。",
        asset_pack="bazi-v1",
        tags=["合盘", "关系", "五行", "地支"],
    )
    input_model = CompatibilityInput
    output_model = CompatibilityOutput

    def execute(
        self,
        request: CompatibilityInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_compatibility(request),
            warnings=["合盘仅供文化娱乐，不应替代真实沟通或关系决策。"],
        )
