from __future__ import annotations

from datetime import datetime as DateTime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.time import localize_datetime, timezone_of


PALACE_DATA: tuple[dict[str, object], ...] = (
    {
        "name": "大安",
        "rating": "吉",
        "element": "木",
        "direction": "东",
        "theme": "安定、守成、循序推进",
        "advice": "宜稳步执行，避免无谓变更。",
    },
    {
        "name": "留连",
        "rating": "平",
        "element": "土",
        "direction": "中央",
        "theme": "拖延、反复、关系牵绊",
        "advice": "先清理阻塞与未决事项，再定期限。",
    },
    {
        "name": "速喜",
        "rating": "吉",
        "element": "火",
        "direction": "南",
        "theme": "消息、加速、短期喜讯",
        "advice": "抓住窗口快速沟通，但要核实细节。",
    },
    {
        "name": "赤口",
        "rating": "凶",
        "element": "金",
        "direction": "西",
        "theme": "口舌、摩擦、规则冲突",
        "advice": "书面确认边界，减少情绪化表达。",
    },
    {
        "name": "小吉",
        "rating": "吉",
        "element": "水",
        "direction": "北",
        "theme": "合作、小成、渐进收益",
        "advice": "适合先做小规模验证，再逐步放大。",
    },
    {
        "name": "空亡",
        "rating": "凶",
        "element": "土",
        "direction": "中央",
        "theme": "落空、信息缺失、重新评估",
        "advice": "暂停重大承诺，补齐事实与资源。",
    },
)


class XiaoliurenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime | None = None
    timezone: str = "Asia/Shanghai"
    lunar_month: int | None = Field(default=None, ge=1, le=12)
    lunar_day: int | None = Field(default=None, ge=1, le=30)
    hour_index: int | None = Field(default=None, ge=1, le=12)
    question: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_timezone(self) -> "XiaoliurenInput":
        timezone_of(self.timezone)
        supplied = (self.lunar_month, self.lunar_day, self.hour_index)
        if any(value is not None for value in supplied) and not all(
            value is not None for value in supplied
        ):
            raise ValueError("手工历数必须同时提供 lunar_month、lunar_day、hour_index。")
        return self


class CountingStep(BaseModel):
    stage: str
    count: int
    palace: str


class XiaoliurenOutput(BaseModel):
    datetime: DateTime
    timezone: str
    question: str | None
    calendar_basis: str
    month_number: int
    day_number: int
    hour_number: int
    steps: list[CountingStep]
    result_palace: str
    rating: str
    element: str
    direction: str
    theme: str
    advice: str
    method_notes: list[str]


def calculate_xiaoliuren(
    request: XiaoliurenInput,
    context: RunContext,
) -> XiaoliurenOutput:
    effective = localize_datetime(
        request.datetime or context.effective_datetime,
        request.timezone,
    )
    if request.lunar_month is not None:
        month_number = request.lunar_month
        day_number = request.lunar_day or 1
        hour_number = request.hour_index or 1
        basis = "manual_lunar_numbers"
    else:
        month_number = effective.month
        day_number = effective.day
        hour_number = ((effective.hour + 1) // 2) % 12 + 1
        basis = "gregorian_fallback"

    month_index = (month_number - 1) % 6
    day_index = (month_index + day_number - 1) % 6
    hour_result_index = (day_index + hour_number - 1) % 6
    result = PALACE_DATA[hour_result_index]
    return XiaoliurenOutput(
        datetime=effective,
        timezone=request.timezone,
        question=request.question,
        calendar_basis=basis,
        month_number=month_number,
        day_number=day_number,
        hour_number=hour_number,
        steps=[
            CountingStep(stage="月", count=month_number, palace=str(PALACE_DATA[month_index]["name"])),
            CountingStep(stage="日", count=day_number, palace=str(PALACE_DATA[day_index]["name"])),
            CountingStep(stage="时", count=hour_number, palace=str(result["name"])),
        ],
        result_palace=str(result["name"]),
        rating=str(result["rating"]),
        element=str(result["element"]),
        direction=str(result["direction"]),
        theme=str(result["theme"]),
        advice=str(result["advice"]),
        method_notes=[
            "从大安起月上数，再从月宫起日上数，最后从日宫起时上数。",
            "未提供农历历数时使用公历数字回退，并在 calendar_basis 中明确标记。",
        ],
    )


@register_pipeline
class XiaoliurenPipeline(Pipeline[XiaoliurenInput, XiaoliurenOutput]):
    manifest = PipelineManifest(
        id="xiaoliuren",
        name="小六壬",
        version="0.1.0",
        ruleset="six-palace-counting-v1",
        category="counting_oracle",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="按月、日、时三步落六宫，输出宫位、五行、方位与结构化断事线索。",
        asset_pack="xiaoliuren-v1",
        tags=["大安", "留连", "速喜", "赤口", "小吉", "空亡"],
    )
    input_model = XiaoliurenInput
    output_model = XiaoliurenOutput

    def execute(
        self,
        request: XiaoliurenInput,
        context: RunContext,
    ) -> PipelineExecution:
        output = calculate_xiaoliuren(request, context)
        warnings = (
            ["未提供农历月日时，当前结果使用公历数字回退。"]
            if output.calendar_basis == "gregorian_fallback"
            else []
        )
        return PipelineExecution(result=output, warnings=warnings)

