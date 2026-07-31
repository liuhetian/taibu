from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline


LINE_RULES = {
    "life_line": {
        "deep": "传统手相把清晰深长视为精力使用较稳定；不代表寿命。",
        "light": "传统手相把浅淡视为精力分配更易受环境影响；不代表健康状况。",
        "broken": "传统手相把分段视为生活节奏的阶段变化；不代表疾病或意外。",
    },
    "head_line": {
        "straight": "传统类象偏向实际、线性的问题处理。",
        "curved": "传统类象偏向联想、图像化与弹性思考。",
        "forked": "传统类象偏向同时容纳现实与想象的多路径判断。",
    },
    "heart_line": {
        "long": "传统类象偏向持续投入关系与清楚表达承诺。",
        "short": "传统类象偏向以行动和边界处理亲密关系。",
        "chained": "传统类象提醒情绪体验可能细腻且层次较多。",
    },
    "fate_line": {
        "clear": "传统类象偏向目标或职业路径较连贯。",
        "faint": "传统类象偏向路径由多种角色共同构成。",
        "absent": "传统类象偏向不以单一事业轨迹定义自我。",
    },
}


class PalmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hand: Literal["left", "right", "both"] = "both"
    life_line: Literal["deep", "light", "broken"]
    head_line: Literal["straight", "curved", "forked"]
    heart_line: Literal["long", "short", "chained"]
    fate_line: Literal["clear", "faint", "absent"]
    palm_shape: Literal["square", "long", "broad", "slender"] = "square"


class PalmObservation(BaseModel):
    line: str
    form: str
    cultural_association: str


class PalmOutput(BaseModel):
    hand: str
    palm_element: str
    observations: list[PalmObservation]
    synthesis: list[str]
    method_notes: list[str]


def calculate_palm(request: PalmInput) -> PalmOutput:
    values = request.model_dump()
    observations = [
        PalmObservation(
            line=line,
            form=values[line],
            cultural_association=LINE_RULES[line][values[line]],
        )
        for line in ("life_line", "head_line", "heart_line", "fate_line")
    ]
    palm_elements = {
        "square": "土型手",
        "long": "水型手",
        "broad": "火型手",
        "slender": "风型手",
    }
    return PalmOutput(
        hand=request.hand,
        palm_element=palm_elements[request.palm_shape],
        observations=observations,
        synthesis=[item.cultural_association for item in observations],
        method_notes=[
            "由调用方提供结构化掌纹观察，内核不处理或存储手部照片。",
            "生命线不表示寿命，任何掌纹都不能诊断疾病或预测事故。",
            "左右手、先后天等分法存在门派差异，本规则仅保留 hand 字段而不作确定性断言。",
        ],
    )


@register_pipeline
class PalmPipeline(Pipeline[PalmInput, PalmOutput]):
    manifest = PipelineManifest(
        id="palm",
        name="手相类象",
        version="0.1.0",
        ruleset="structured-four-lines-v1",
        category="physiognomy",
        tradition="cross_cultural",
        mode=PipelineMode.ASSESSMENT,
        summary="把结构化掌纹与掌形观察映射为传统类象，明确排除寿命和健康推断。",
        asset_pack="physiognomy-v1",
        tags=["掌纹", "掌形", "结构化观察"],
    )
    input_model = PalmInput
    output_model = PalmOutput

    def execute(self, request: PalmInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_palm(request),
            warnings=["手相仅供文化娱乐，不可用于医疗、寿命或事故判断。"],
        )
