from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline


# direction +1 means agreement supports the first pole, -1 supports the second.
QUESTION_BANK: dict[str, tuple[str, str, int]] = {
    "ei01": ("E-I", "连续社交后我通常更有精力。", 1),
    "ei02": ("E-I", "我更愿意先独自整理想法再表达。", -1),
    "ei03": ("E-I", "在陌生群体中我会主动开启话题。", 1),
    "ei04": ("E-I", "长时间独处能帮助我恢复状态。", -1),
    "ei05": ("E-I", "我常在说话过程中形成想法。", 1),
    "ei06": ("E-I", "我倾向维持少量而深入的关系。", -1),
    "sn01": ("S-N", "我先关注可验证的具体事实。", -1),
    "sn02": ("S-N", "我容易从信息中联想到未来可能。", 1),
    "sn03": ("S-N", "我偏好清楚、逐步的操作说明。", -1),
    "sn04": ("S-N", "我喜欢寻找模式、隐喻和整体结构。", 1),
    "sn05": ("S-N", "我更信任直接经验而非推测。", -1),
    "sn06": ("S-N", "重复成熟流程比探索新方法更让我安心。", -1),
    "tf01": ("T-F", "做决定时我优先考虑一致的原则。", 1),
    "tf02": ("T-F", "我会优先考虑决定对人的影响。", -1),
    "tf03": ("T-F", "即使意见尖锐，我也重视逻辑准确。", 1),
    "tf04": ("T-F", "维护关系有时比证明正确更重要。", -1),
    "tf05": ("T-F", "我容易发现论证中的漏洞。", 1),
    "tf06": ("T-F", "他人的情绪会显著影响我的判断。", -1),
    "jp01": ("J-P", "我喜欢尽早确定计划与截止日期。", 1),
    "jp02": ("J-P", "保留选择直到最后让我更自在。", -1),
    "jp03": ("J-P", "完成事项比启动新事项更有满足感。", 1),
    "jp04": ("J-P", "环境变化时我会自然调整原计划。", -1),
    "jp05": ("J-P", "清晰结构能提升我的效率。", 1),
    "jp06": ("J-P", "我更喜欢探索过程而非固定步骤。", -1),
}


class MbtiInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    responses: dict[str, Annotated[int, Field(ge=-3, le=3)]] = Field(
        min_length=8,
        description="-3 强烈不同意，0 中立，+3 强烈同意",
    )

    @model_validator(mode="after")
    def validate_ids(self) -> "MbtiInput":
        unknown = sorted(set(self.responses) - set(QUESTION_BANK))
        if unknown:
            raise ValueError(f"未知题目编号：{', '.join(unknown)}")
        return self


class MbtiDimension(BaseModel):
    dimension: str
    first_pole: str
    second_pole: str
    score: int
    preference: str
    strength_percent: float
    answered: int


class MbtiOutput(BaseModel):
    type: str
    dimensions: list[MbtiDimension]
    answered: int
    total_questions: int
    completion_percent: float
    method_notes: list[str]


def calculate_mbti(request: MbtiInput) -> MbtiOutput:
    scores = {"E-I": 0, "S-N": 0, "T-F": 0, "J-P": 0}
    counts = {key: 0 for key in scores}
    for question_id, response in request.responses.items():
        dimension, _, direction = QUESTION_BANK[question_id]
        scores[dimension] += response * direction
        counts[dimension] += 1

    dimensions: list[MbtiDimension] = []
    type_letters: list[str] = []
    for dimension in ("E-I", "S-N", "T-F", "J-P"):
        first, second = dimension.split("-")
        score = scores[dimension]
        preference = first if score >= 0 else second
        type_letters.append(preference)
        maximum = max(1, counts[dimension] * 3)
        dimensions.append(
            MbtiDimension(
                dimension=dimension,
                first_pole=first,
                second_pole=second,
                score=score,
                preference=preference,
                strength_percent=round(abs(score) / maximum * 100, 2),
                answered=counts[dimension],
            )
        )
    return MbtiOutput(
        type="".join(type_letters),
        dimensions=dimensions,
        answered=len(request.responses),
        total_questions=len(QUESTION_BANK),
        completion_percent=round(len(request.responses) / len(QUESTION_BANK) * 100, 2),
        method_notes=[
            "这是偏好量表，不测量能力、价值或心理健康。",
            "未答满题目时仍返回暂定类型，并以 completion_percent 标记完整度。",
        ],
    )


@register_pipeline
class MbtiPipeline(Pipeline[MbtiInput, MbtiOutput]):
    manifest = PipelineManifest(
        id="mbti",
        name="MBTI 偏好量表",
        version="0.1.0",
        ruleset="four-dimension-24-item-v1",
        category="assessment",
        tradition="psychometric_inspired",
        mode=PipelineMode.ASSESSMENT,
        summary="使用仓库内置 24 题对四个偏好维度计分，输出类型与强度。",
        asset_pack="mbti-v1",
        tags=["E-I", "S-N", "T-F", "J-P"],
    )
    input_model = MbtiInput
    output_model = MbtiOutput

    def execute(self, request: MbtiInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_mbti(request),
            warnings=["本量表不是官方 MBTI 评估，也不用于临床或招聘决策。"],
        )

