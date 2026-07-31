from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import EARTHLY_BRANCHES, HEAVENLY_STEMS
from ..ziwei import FOUR_TRANSFORMATIONS, PALACE_BRANCHES, ZiweiInput, calculate_ziwei


class ZiweiHoroscopeInput(ZiweiInput):
    target_year: int = Field(ge=1600, le=2600)
    target_lunar_month: int = Field(default=1, ge=1, le=12)
    target_lunar_day: int = Field(default=1, ge=1, le=30)
    target_hour_branch: Literal[
        "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"
    ] = "子"


class ActivatedPalace(BaseModel):
    layer: str
    palace_name: str
    branch: str
    reason: str


class ZiweiHoroscopeOutput(BaseModel):
    nominal_age: int
    direction: Literal["forward", "backward"]
    decade_number: int
    decade_age_range: list[int]
    decade_palace: str
    annual_palace: str
    monthly_palace: str
    daily_palace: str
    hourly_palace: str
    annual_transformations: dict[str, str]
    activated_palaces: list[ActivatedPalace]
    method_notes: list[str]


def calculate_horoscope(request: ZiweiHoroscopeInput) -> ZiweiHoroscopeOutput:
    natal = calculate_ziwei(
        ZiweiInput.model_validate(
            request.model_dump(
                include={
                    "lunar_year",
                    "lunar_month",
                    "lunar_day",
                    "hour_branch",
                    "gender",
                    "leap_month",
                }
            )
        )
    )
    life_index = next(index for index, palace in enumerate(natal.palaces) if palace.name == "命宫")
    year_stem = natal.year_pillar[0]
    year_yang = HEAVENLY_STEMS.index(year_stem) % 2 == 0
    forward = (
        request.gender == "male"
        and year_yang
        or request.gender == "female"
        and not year_yang
        or request.gender == "unspecified"
    )
    step = 1 if forward else -1
    nominal_age = request.target_year - request.lunar_year + 1
    decade_number = max(0, (nominal_age - natal.bureau_number) // 10)
    decade_index = (life_index + step * decade_number) % 12
    decade_start = natal.bureau_number + decade_number * 10

    target_year_index = (request.target_year - 4) % 60
    annual_index = PALACE_BRANCHES.index(EARTHLY_BRANCHES[target_year_index % 12])
    monthly_index = (annual_index + request.target_lunar_month - 1) % 12
    daily_index = (monthly_index + request.target_lunar_day - 1) % 12
    hourly_index = (daily_index + EARTHLY_BRANCHES.index(request.target_hour_branch)) % 12
    indexes = (
        ("大限", decade_index, "十年运限所在宫"),
        ("流年", annual_index, "目标年支定位"),
        ("流月", monthly_index, "由流年宫顺数农历月"),
        ("流日", daily_index, "由流月宫顺数农历日"),
        ("流时", hourly_index, "由流日宫顺数时支"),
    )
    activated = [
        ActivatedPalace(
            layer=layer,
            palace_name=natal.palaces[index].name,
            branch=natal.palaces[index].branch,
            reason=reason,
        )
        for layer, index, reason in indexes
    ]
    target_stem = HEAVENLY_STEMS[target_year_index % 10]
    return ZiweiHoroscopeOutput(
        nominal_age=nominal_age,
        direction="forward" if forward else "backward",
        decade_number=decade_number + 1,
        decade_age_range=[decade_start, decade_start + 9],
        decade_palace=natal.palaces[decade_index].name,
        annual_palace=natal.palaces[annual_index].name,
        monthly_palace=natal.palaces[monthly_index].name,
        daily_palace=natal.palaces[daily_index].name,
        hourly_palace=natal.palaces[hourly_index].name,
        annual_transformations=FOUR_TRANSFORMATIONS[target_stem],
        activated_palaces=activated,
        method_notes=[
            "以五行局数为首限起始年龄，按生年阴阳与性别顺逆行十二宫。",
            "流年以目标年支定位，流月、流日、流时在当前规则中逐层顺数。",
            "运限输出是结构定位层；事件解释应结合本命星曜与现实信息。",
        ],
    )


@register_pipeline
class ZiweiHoroscopePipeline(Pipeline[ZiweiHoroscopeInput, ZiweiHoroscopeOutput]):
    manifest = PipelineManifest(
        id="ziwei_horoscope",
        name="紫微运限",
        version="0.1.0",
        ruleset="bureau-decade-layered-limits-v1",
        category="fortune_cycle",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="基于本命十二宫定位大限、流年、流月、流日与流时，并给出流年四化。",
        asset_pack="ziwei-v1",
        tags=["大限", "流年", "流月", "流日", "流时"],
    )
    input_model = ZiweiHoroscopeInput
    output_model = ZiweiHoroscopeOutput

    def execute(
        self,
        request: ZiweiHoroscopeInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(result=calculate_horoscope(request))
