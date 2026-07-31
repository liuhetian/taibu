from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline


FACE_RULES = {
    "forehead": {
        "broad": ("天庭", "开阔", "传统类象偏向规划与早年学习环境"),
        "balanced": ("天庭", "均衡", "传统类象偏向循序推进"),
        "narrow": ("天庭", "紧凑", "传统类象提醒减少早期压力的内化"),
    },
    "eyebrows": {
        "clear": ("保寿官", "清秀", "传统类象偏向条理与人际边界"),
        "dense": ("保寿官", "浓密", "传统类象偏向行动力与直接表达"),
        "sparse": ("保寿官", "疏淡", "传统类象偏向审慎与独立判断"),
    },
    "eyes": {
        "bright": ("监察官", "有神", "传统类象偏向观察力与响应速度"),
        "soft": ("监察官", "柔和", "传统类象偏向共情与缓和沟通"),
        "deep": ("监察官", "深邃", "传统类象偏向内省与保留"),
    },
    "nose": {
        "straight": ("审辨官", "端直", "传统类象偏向稳定执行与资源秩序"),
        "rounded": ("审辨官", "丰圆", "传统类象偏向包容与资源整合"),
        "slender": ("审辨官", "秀长", "传统类象偏向细节与谨慎配置"),
    },
    "mouth": {
        "defined": ("出纳官", "轮廓清晰", "传统类象偏向表达有界限"),
        "full": ("出纳官", "丰厚", "传统类象偏向情感表达与分享"),
        "thin": ("出纳官", "薄敛", "传统类象偏向克制与信息筛选"),
    },
    "chin": {
        "rounded": ("地阁", "圆厚", "传统类象偏向后期稳定与支持网络"),
        "square": ("地阁", "方正", "传统类象偏向坚持与责任"),
        "pointed": ("地阁", "尖秀", "传统类象偏向灵活与审美取向"),
    },
}


class FaceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forehead: Literal["broad", "balanced", "narrow"]
    eyebrows: Literal["clear", "dense", "sparse"]
    eyes: Literal["bright", "soft", "deep"]
    nose: Literal["straight", "rounded", "slender"]
    mouth: Literal["defined", "full", "thin"]
    chin: Literal["rounded", "square", "pointed"]
    facial_balance: Literal["balanced", "left_emphasis", "right_emphasis"] = "balanced"


class FaceObservation(BaseModel):
    feature: str
    traditional_office: str
    observed_form: str
    cultural_association: str


class FaceOutput(BaseModel):
    observations: list[FaceObservation]
    balance_note: str
    recurring_themes: list[str]
    method_notes: list[str]


def calculate_face(request: FaceInput) -> FaceOutput:
    observations: list[FaceObservation] = []
    themes: list[str] = []
    values = request.model_dump()
    for feature in ("forehead", "eyebrows", "eyes", "nose", "mouth", "chin"):
        office, form, association = FACE_RULES[feature][values[feature]]
        observations.append(
            FaceObservation(
                feature=feature,
                traditional_office=office,
                observed_form=form,
                cultural_association=association,
            )
        )
        themes.append(association.removeprefix("传统类象偏向").removeprefix("传统类象提醒"))
    balance_notes = {
        "balanced": "输入描述为左右均衡；传统框架会优先综合全脸，不放大单一部位。",
        "left_emphasis": "输入描述为左侧更显著；仅记录形态差异，不将不对称解释为健康信息。",
        "right_emphasis": "输入描述为右侧更显著；仅记录形态差异，不将不对称解释为健康信息。",
    }
    return FaceOutput(
        observations=observations,
        balance_note=balance_notes[request.facial_balance],
        recurring_themes=themes,
        method_notes=[
            "由调用方提供结构化外观观察，内核不识别人脸、不存储照片。",
            "输出是传统面相术语的文化映射，不从外貌推断人格、健康、族裔或能力。",
        ],
    )


@register_pipeline
class FacePipeline(Pipeline[FaceInput, FaceOutput]):
    manifest = PipelineManifest(
        id="face",
        name="面相类象",
        version="0.1.0",
        ruleset="structured-five-offices-v1",
        category="physiognomy",
        tradition="chinese",
        mode=PipelineMode.ASSESSMENT,
        summary="将用户主动填写的面部形态映射为五官、天庭与地阁的传统文化类象。",
        asset_pack="physiognomy-v1",
        tags=["五官", "天庭", "地阁", "结构化观察"],
    )
    input_model = FaceInput
    output_model = FaceOutput

    def execute(self, request: FaceInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_face(request),
            warnings=["请勿依据外貌类象作出招聘、医疗、信用或其他高影响决策。"],
        )
