from __future__ import annotations

from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import four_pillars
from ...shared.time import gregorian_jdn, localize_datetime, solar_longitude, timezone_of


PALACE_SEQUENCE = (1, 8, 3, 4, 9, 2, 7, 6)
PALACE_DIRECTIONS = {
    1: "正北",
    2: "西南",
    3: "正东",
    4: "东南",
    5: "中宫",
    6: "西北",
    7: "正西",
    8: "东北",
    9: "正南",
}
NINE_STARS = (
    ("太乙", "统摄与中枢"),
    ("摄提", "启动与牵引"),
    ("轩辕", "秩序与统合"),
    ("招摇", "变化与传播"),
    ("天符", "规则与约束"),
    ("青龙", "生发与协同"),
    ("咸池", "吸引与耗散"),
    ("太阴", "蓄藏与谋划"),
    ("天乙", "援助与转圜"),
)


class TaiyiInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime
    timezone: str = "Asia/Shanghai"
    scale: Literal["day", "hour"] = "day"
    question: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_timezone(self) -> "TaiyiInput":
        timezone_of(self.timezone)
        return self


class TaiyiStar(BaseModel):
    name: str
    palace: int
    direction: str
    theme: str


class TaiyiOutput(BaseModel):
    datetime: DateTime
    scale: str
    dun_type: Literal["阳遁", "阴遁"]
    ju_number: int
    epoch_count: int
    day_pillar: str
    hour_pillar: str
    taiyi_palace: int
    host_general_palace: int
    guest_general_palace: int
    fixed_eye_palace: int
    stars: list[TaiyiStar]
    interactions: list[str]
    method_notes: list[str]


def calculate_taiyi(request: TaiyiInput) -> TaiyiOutput:
    effective = localize_datetime(request.datetime, request.timezone)
    pillars = four_pillars(effective, day_boundary="zi_hour")
    longitude = solar_longitude(effective)
    yang_dun = longitude >= 270 or longitude < 90
    jdn = gregorian_jdn(effective.year, effective.month, effective.day)
    day_count = jdn - gregorian_jdn(2000, 1, 7)
    epoch_count = day_count if request.scale == "day" else day_count * 12 + (
        (effective.hour + 1) // 2
    )
    cycle_index = epoch_count % 72
    ju = cycle_index + 1 if yang_dun else 72 - cycle_index
    direction = 1 if yang_dun else -1

    taiyi_index = (ju - 1) % 8
    taiyi_palace = PALACE_SEQUENCE[taiyi_index]
    fixed_eye = PALACE_SEQUENCE[(taiyi_index + (ju - 1) // 8 + 2) % 8]
    host = PALACE_SEQUENCE[(taiyi_index + pillars.day.index % 8) % 8]
    guest = PALACE_SEQUENCE[(taiyi_index + pillars.hour.index % 8 + 4) % 8]

    stars: list[TaiyiStar] = []
    for index, (name, theme) in enumerate(NINE_STARS):
        if index == 0:
            palace = taiyi_palace
        elif index == 4:
            palace = 5
        else:
            step = index if index < 5 else index - 1
            palace = PALACE_SEQUENCE[(taiyi_index + direction * step) % 8]
        stars.append(
            TaiyiStar(
                name=name,
                palace=palace,
                direction=PALACE_DIRECTIONS[palace],
                theme=theme,
            )
        )

    interactions: list[str] = []
    if host == guest:
        interactions.append("主客同宫：双方关注点集中，竞争或协作会被放大。")
    if taiyi_palace in {host, guest}:
        interactions.append("主将或客将与太乙同宫：中枢因素直接介入。")
    if fixed_eye in {host, guest}:
        interactions.append("定目与主客将相逢：议题焦点较集中。")
    if not interactions:
        interactions.append("太乙、定目与主客将分宫：局面由多处因素共同推动。")

    return TaiyiOutput(
        datetime=effective,
        scale=request.scale,
        dun_type="阳遁" if yang_dun else "阴遁",
        ju_number=ju,
        epoch_count=epoch_count,
        day_pillar=pillars.day.name,
        hour_pillar=pillars.hour.name,
        taiyi_palace=taiyi_palace,
        host_general_palace=host,
        guest_general_palace=guest,
        fixed_eye_palace=fixed_eye,
        stars=stars,
        interactions=interactions,
        method_notes=[
            "以冬至至夏至为阳遁、夏至至冬至为阴遁的太阳黄经半周划分。",
            "采用七十二局循环；2000-01-07 为仓库规则锚点，日计与时计共享同一可复现纪元。",
            "太乙按八宫序运行，中五宫留给天符；主客将与定目按干支序数派生。",
            "太乙神数存在年计、月计、日计、时计及不同纪元法；规则差异由 ruleset 隔离。",
        ],
    )


@register_pipeline
class TaiyiPipeline(Pipeline[TaiyiInput, TaiyiOutput]):
    manifest = PipelineManifest(
        id="taiyi",
        name="太乙神数",
        version="0.1.0",
        ruleset="solar-half-year-72-ju-v1",
        category="time_divination",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="计算日计或时计七十二局、太乙八宫、定目、主客将与太乙九星。",
        asset_pack="taiyi-v1",
        tags=["七十二局", "太乙九星", "主客将", "定目"],
    )
    input_model = TaiyiInput
    output_model = TaiyiOutput

    def execute(self, request: TaiyiInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_taiyi(request),
            warnings=["太乙纪元法门派差异显著；跨软件比较时必须同时核对 ruleset。"],
        )
