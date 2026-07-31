from __future__ import annotations

from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import (
    AssetReference,
    Pipeline,
    PipelineExecution,
    PipelineManifest,
    PipelineMode,
    RunContext,
)
from ...registry import register_pipeline
from ...shared.ganzhi import (
    BRANCH_ELEMENTS,
    HIDDEN_STEMS,
    STEM_ELEMENTS,
    FourPillars,
    branch_relations,
    five_element_statistics,
    four_pillars,
    kongwang_of,
    nayin_of,
    ten_god,
    yin_yang_of_branch,
    yin_yang_of_stem,
)
from ...shared.time import (
    localize_datetime,
    solar_term_at,
    timezone_of,
    true_solar_datetime,
)


class BaziInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime = Field(description="出生时间；无偏移量时按 timezone 解释")
    timezone: str = "Asia/Shanghai"
    gender: Literal["male", "female", "unspecified"] = "unspecified"
    longitude: float | None = Field(default=None, ge=-180, le=180)
    true_solar_time: bool = False
    day_boundary: Literal["midnight", "zi_hour"] = "midnight"

    @model_validator(mode="after")
    def validate_context(self) -> "BaziInput":
        timezone_of(self.timezone)
        if self.true_solar_time and self.longitude is None:
            raise ValueError("启用 true_solar_time 时必须提供 longitude。")
        return self


class HiddenStemInfo(BaseModel):
    stem: str
    element: str
    ten_god: str
    weight: float


class PillarInfo(BaseModel):
    name: str
    stem: str
    branch: str
    ganzhi: str
    cycle_index: int = Field(ge=0, le=59)
    stem_element: str
    branch_element: str
    stem_yin_yang: str
    branch_yin_yang: str
    ten_god: str
    hidden_stems: list[HiddenStemInfo]
    nayin: str
    is_kongwang: bool


class TimeCorrection(BaseModel):
    civil_datetime: DateTime
    effective_datetime: DateTime
    timezone: str
    true_solar_time: bool
    correction_minutes: float


class SolarTermInfo(BaseModel):
    name: str
    longitude: float
    phase_degrees: float
    approximate_start: DateTime


class BaziOutput(BaseModel):
    time: TimeCorrection
    solar_term: SolarTermInfo
    gender: str
    day_master: dict[str, str]
    four_pillars: dict[str, PillarInfo]
    five_elements: dict[str, float]
    dominant_element: str
    weakest_element: str
    kongwang: list[str]
    branch_relations: list[dict[str, str]]
    method_notes: list[str]


def _pillar_model(
    label: str,
    value,
    *,
    day_stem: str,
    kongwang: tuple[str, str],
    is_day: bool = False,
) -> PillarInfo:
    weights = (0.6, 0.3, 0.1)
    hidden = [
        HiddenStemInfo(
            stem=stem,
            element=STEM_ELEMENTS[stem],
            ten_god=ten_god(day_stem, stem),
            weight=weights[index],
        )
        for index, stem in enumerate(HIDDEN_STEMS[value.branch])
    ]
    return PillarInfo(
        name=label,
        stem=value.stem,
        branch=value.branch,
        ganzhi=value.name,
        cycle_index=value.index,
        stem_element=STEM_ELEMENTS[value.stem],
        branch_element=BRANCH_ELEMENTS[value.branch],
        stem_yin_yang=yin_yang_of_stem(value.stem),
        branch_yin_yang=yin_yang_of_branch(value.branch),
        ten_god="日主" if is_day else ten_god(day_stem, value.stem),
        hidden_stems=hidden,
        nayin=nayin_of(value.index),
        is_kongwang=value.branch in kongwang,
    )


def calculate_bazi(request: BaziInput) -> BaziOutput:
    civil = localize_datetime(request.datetime, request.timezone)
    correction_minutes = 0.0
    effective = civil
    if request.true_solar_time:
        assert request.longitude is not None
        effective, correction_minutes = true_solar_datetime(civil, request.longitude)

    term = solar_term_at(effective)
    pillars: FourPillars = four_pillars(
        effective,
        day_boundary=request.day_boundary,
    )
    kongwang = kongwang_of(pillars.day.index)
    stats = five_element_statistics(pillars)
    ordered = sorted(stats.items(), key=lambda item: (item[1], item[0]))
    day_element = STEM_ELEMENTS[pillars.day.stem]

    return BaziOutput(
        time=TimeCorrection(
            civil_datetime=civil,
            effective_datetime=effective,
            timezone=request.timezone,
            true_solar_time=request.true_solar_time,
            correction_minutes=round(correction_minutes, 4),
        ),
        solar_term=SolarTermInfo(
            name=term.name,
            longitude=term.longitude,
            phase_degrees=term.phase_degrees,
            approximate_start=term.approximate_start,
        ),
        gender=request.gender,
        day_master={
            "stem": pillars.day.stem,
            "element": day_element,
            "yin_yang": yin_yang_of_stem(pillars.day.stem),
        },
        four_pillars={
            "year": _pillar_model(
                "年柱", pillars.year, day_stem=pillars.day.stem, kongwang=kongwang
            ),
            "month": _pillar_model(
                "月柱", pillars.month, day_stem=pillars.day.stem, kongwang=kongwang
            ),
            "day": _pillar_model(
                "日柱",
                pillars.day,
                day_stem=pillars.day.stem,
                kongwang=kongwang,
                is_day=True,
            ),
            "hour": _pillar_model(
                "时柱", pillars.hour, day_stem=pillars.day.stem, kongwang=kongwang
            ),
        },
        five_elements=stats,
        dominant_element=ordered[-1][0],
        weakest_element=ordered[0][0],
        kongwang=list(kongwang),
        branch_relations=branch_relations(pillars),
        method_notes=[
            "年柱以立春为岁界，月柱以十二节为月界。",
            f"日界采用：{request.day_boundary}。",
            "太阳黄经使用仓库内置的紧凑天文级数计算，不调用外部历书服务。",
            "五行统计包含天干、地支本气与藏干权重，仅作为结构化描述。",
        ],
    )


@register_pipeline
class BaziPipeline(Pipeline[BaziInput, BaziOutput]):
    manifest = PipelineManifest(
        id="bazi",
        name="八字四柱",
        version="0.1.0",
        ruleset="solar-terms-four-pillars-v1",
        category="natal_chart",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="基于出生时间、时区与可选真太阳时计算四柱、十神与五行结构。",
        asset_pack="bazi-v1",
        tags=["四柱", "干支", "十神", "五行"],
    )
    input_model = BaziInput
    output_model = BaziOutput

    def execute(
        self,
        request: BaziInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_bazi(request),
            assets=[
                AssetReference(
                    id="bazi.cover",
                    pack="bazi-v1",
                    role="pipeline-cover",
                    path="assets/packs/bazi/cover.png",
                    media_type="image/png",
                    status="available",
                )
            ],
            notes=["同一输入在同一规则版本下产生相同命盘。"],
        )
