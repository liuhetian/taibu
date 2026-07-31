from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from datetime import time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import (
    SIX_CLASHES,
    SIX_COMBINATIONS,
    SIX_HARMS,
    STEM_ELEMENTS,
    five_element_statistics,
    four_pillars,
    ten_god,
)
from ...shared.time import localize_datetime

TEN_GOD_DOMAIN = {
    "比肩": "self",
    "劫财": "collaboration",
    "食神": "creativity",
    "伤官": "expression",
    "偏财": "resources",
    "正财": "resources",
    "七杀": "pressure",
    "正官": "responsibility",
    "偏印": "learning",
    "正印": "support",
}


class FortuneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_datetime: DateTime
    timezone: str = "Asia/Shanghai"
    target_date: Date
    granularity: Literal["daily", "monthly"] = "daily"
    periods: int = Field(default=7, ge=1, le=36)

    @model_validator(mode="after")
    def validate_timezone(self) -> FortuneInput:
        localize_datetime(self.birth_datetime, self.timezone)
        return self


class FortunePeriod(BaseModel):
    start: Date
    transit_pillar: str
    ten_god: str
    focus_domain: str
    supportive_relations: list[str]
    tension_relations: list[str]
    balance_index: float
    prompts: list[str]


class FortuneOutput(BaseModel):
    natal_pillars: list[str]
    day_master: str
    granularity: str
    periods: list[FortunePeriod]
    method_notes: list[str]


def _add_month(value: Date, months: int) -> Date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(absolute, 12)
    return Date(year, month_zero + 1, 1)


def calculate_fortune(request: FortuneInput) -> FortuneOutput:
    birth = localize_datetime(request.birth_datetime, request.timezone)
    natal = four_pillars(birth)
    natal_stats = five_element_statistics(natal)
    natal_branches = (natal.year.branch, natal.month.branch, natal.day.branch, natal.hour.branch)
    periods: list[FortunePeriod] = []
    for offset in range(request.periods):
        target = (
            request.target_date + timedelta(days=offset)
            if request.granularity == "daily"
            else _add_month(request.target_date, offset)
        )
        moment = localize_datetime(DateTime.combine(target, time(12)), request.timezone)
        transit_four = four_pillars(moment)
        transit = transit_four.day if request.granularity == "daily" else transit_four.month
        god = ten_god(natal.day.stem, transit.stem)
        supportive: list[str] = []
        tensions: list[str] = []
        for branch in natal_branches:
            pair = frozenset((branch, transit.branch))
            if pair in SIX_COMBINATIONS:
                supportive.append(f"{branch}{transit.branch}六合")
            if pair in SIX_CLASHES:
                tensions.append(f"{branch}{transit.branch}六冲")
            if pair in SIX_HARMS:
                tensions.append(f"{branch}{transit.branch}六害")
        transit_element = STEM_ELEMENTS[transit.stem]
        mean = sum(natal_stats.values()) / 5
        balance = 60 + min(20, natal_stats[transit_element] / max(mean, 0.1) * 10)
        balance += min(15, len(supportive) * 5)
        balance -= min(25, len(tensions) * 5)
        prompts = [
            f"把{TEN_GOD_DOMAIN[god]}主题落实为一个可检查的小行动。",
            "若出现冲害，优先核对时间、边界和沟通假设。",
        ]
        periods.append(
            FortunePeriod(
                start=target,
                transit_pillar=transit.name,
                ten_god=god,
                focus_domain=TEN_GOD_DOMAIN[god],
                supportive_relations=supportive,
                tension_relations=tensions,
                balance_index=round(max(0, min(100, balance)), 2),
                prompts=prompts,
            )
        )
    return FortuneOutput(
        natal_pillars=[natal.year.name, natal.month.name, natal.day.name, natal.hour.name],
        day_master=natal.day.stem,
        granularity=request.granularity,
        periods=periods,
        method_notes=[
            "日运比较流日，月运比较节令月柱；均以出生八字日主为参照。",
            "balance_index 是透明的结构指数，不是事件概率。",
            "此管线只生成规则结果，不调用语言模型撰写个性化断语。",
        ],
    )


@register_pipeline
class FortunePipeline(Pipeline[FortuneInput, FortuneOutput]):
    manifest = PipelineManifest(
        id="fortune",
        name="日月运势",
        version="0.1.0",
        ruleset="natal-transit-structure-v1",
        category="fortune_cycle",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="比较出生四柱与连续流日或流月，输出十神焦点、地支互动与结构指数。",
        asset_pack="bazi-v1",
        tags=["流日", "流月", "十神", "趋势"],
    )
    input_model = FortuneInput
    output_model = FortuneOutput

    def execute(self, request: FortuneInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_fortune(request),
            warnings=["趋势指数不应用于医疗、投资、法律或安全决策。"],
        )
