from __future__ import annotations

from datetime import date as Date, datetime as DateTime, time, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import EARTHLY_BRANCHES, four_pillars, sexagenary_index
from ...shared.time import localize_datetime, timezone_of


class BaziResolveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year_pillar: str = Field(pattern=r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$")
    month_pillar: str = Field(pattern=r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$")
    day_pillar: str = Field(pattern=r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$")
    hour_pillar: str = Field(pattern=r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$")
    start_year: int = Field(default=1900, ge=1600, le=2600)
    end_year: int = Field(default=2100, ge=1600, le=2600)
    timezone: str = "Asia/Shanghai"
    max_results: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_request(self) -> "BaziResolveInput":
        timezone_of(self.timezone)
        if self.end_year < self.start_year:
            raise ValueError("end_year 不得早于 start_year。")
        if self.end_year - self.start_year > 300:
            raise ValueError("单次反查跨度不得超过 300 年。")
        for value in (
            self.year_pillar,
            self.month_pillar,
            self.day_pillar,
            self.hour_pillar,
        ):
            sexagenary_index(value[0], value[1])
        return self


class BirthCandidate(BaseModel):
    representative_datetime: DateTime
    hour_window: str
    pillars: list[str]


class BaziResolveOutput(BaseModel):
    query: list[str]
    range: dict[str, int]
    candidates: list[BirthCandidate]
    truncated: bool
    scanned_days: int
    method_notes: list[str]


def calculate_resolve(request: BaziResolveInput) -> BaziResolveOutput:
    start = Date(request.start_year, 1, 1)
    end = Date(request.end_year, 12, 31)
    current = start
    scanned = 0
    candidates: list[BirthCandidate] = []
    target = (
        request.year_pillar,
        request.month_pillar,
        request.day_pillar,
        request.hour_pillar,
    )
    target_hour_branch = request.hour_pillar[1]
    branch_index = EARTHLY_BRANCHES.index(target_hour_branch)
    representative_hour = (branch_index * 2) % 24
    truncated = False
    while current <= end:
        scanned += 1
        noon = localize_datetime(DateTime.combine(current, time(12)), request.timezone)
        noon_pillars = four_pillars(noon)
        if noon_pillars.day.name == request.day_pillar:
            moment = localize_datetime(
                DateTime.combine(current, time(representative_hour)),
                request.timezone,
            )
            values = four_pillars(moment, day_boundary="midnight")
            names = (
                values.year.name,
                values.month.name,
                values.day.name,
                values.hour.name,
            )
            if names == target:
                start_hour = (representative_hour - 1) % 24
                end_hour = representative_hour % 24
                candidates.append(
                    BirthCandidate(
                        representative_datetime=moment,
                        hour_window=f"{start_hour:02d}:00-{end_hour:02d}:59",
                        pillars=list(names),
                    )
                )
                if len(candidates) >= request.max_results:
                    truncated = current < end
                    break
        current += timedelta(days=1)
    return BaziResolveOutput(
        query=list(target),
        range={"start_year": request.start_year, "end_year": request.end_year},
        candidates=candidates,
        truncated=truncated,
        scanned_days=scanned,
        method_notes=[
            "先按日柱筛选日期，再在目标时支的代表时刻核验完整四柱。",
            "候选窗口是民用钟表两小时范围；节令边界附近应再用具体分钟复核。",
            "反查无法唯一确定地点、经度、真太阳时、历法记录误差或采用的日界门派。",
        ],
    )


@register_pipeline
class BaziResolvePipeline(Pipeline[BaziResolveInput, BaziResolveOutput]):
    manifest = PipelineManifest(
        id="bazi_pillars_resolve",
        name="八字四柱反查",
        version="0.1.0",
        ruleset="bounded-calendar-search-v1",
        category="natal_chart_utility",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="在限定年份范围内由四柱反查可能的公历日期与时辰窗口。",
        asset_pack="bazi-v1",
        tags=["四柱反查", "候选出生时间", "历法搜索"],
    )
    input_model = BaziResolveInput
    output_model = BaziResolveOutput

    def execute(self, request: BaziResolveInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_resolve(request),
            warnings=["四柱反查只返回候选，不足以证明唯一出生时间。"],
        )
