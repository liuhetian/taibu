from __future__ import annotations

from collections import Counter
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline


class MotifDefinition(TypedDict):
    id: str
    keywords: tuple[str, ...]
    theme: str
    questions: tuple[str, ...]


MOTIFS: tuple[MotifDefinition, ...] = (
    {
        "id": "water",
        "keywords": ("水", "海", "河", "雨", "洪水", "游泳"),
        "theme": "情绪与适应",
        "questions": ("水是平静还是汹涌？", "你在水中有控制感吗？"),
    },
    {
        "id": "flight",
        "keywords": ("飞", "飞翔", "漂浮", "天空"),
        "theme": "自由与视角",
        "questions": ("飞行是主动还是失控？", "你想摆脱什么限制？"),
    },
    {
        "id": "fall",
        "keywords": ("坠落", "掉下", "摔", "下坠"),
        "theme": "失控与不确定",
        "questions": ("现实中哪件事缺少支撑？", "落下前发生了什么？"),
    },
    {
        "id": "chase",
        "keywords": ("追", "逃跑", "被抓", "躲藏"),
        "theme": "压力与回避",
        "questions": ("追逐者代表哪种压力？", "如果停下来会发生什么？"),
    },
    {
        "id": "teeth",
        "keywords": ("牙", "牙齿", "掉牙"),
        "theme": "表达与脆弱感",
        "questions": ("近期是否担心形象或表达？", "梦里有疼痛或羞耻吗？"),
    },
    {
        "id": "house",
        "keywords": ("房子", "房间", "家", "门", "地下室"),
        "theme": "自我结构与边界",
        "questions": ("哪个房间最突出？", "空间是熟悉还是陌生？"),
    },
    {
        "id": "death",
        "keywords": ("死亡", "去世", "葬礼", "尸体"),
        "theme": "结束与转变",
        "questions": ("结束的是关系、身份还是阶段？", "梦中的情绪是什么？"),
    },
    {
        "id": "animal",
        "keywords": ("猫", "狗", "蛇", "鸟", "老虎", "动物"),
        "theme": "本能与投射",
        "questions": ("动物的行为像你的哪部分？", "你与它亲近还是对抗？"),
    },
    {
        "id": "exam",
        "keywords": ("考试", "迟到", "作业", "学校", "答题"),
        "theme": "评价与准备",
        "questions": ("近期有哪些被评价的场景？", "你觉得准备充分吗？"),
    },
    {
        "id": "ancestor",
        "keywords": ("祖先", "祖师", "去世的亲人", "老人", "神仙", "天师"),
        "theme": "传承、记忆与价值",
        "questions": ("对方传递的是情绪还是明确内容？", "它唤起了哪段家族或文化记忆？"),
    },
)


class DreamInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dream: str = Field(min_length=1, max_length=10000)
    emotions: list[str] = Field(default_factory=list, max_length=20)
    recurring: bool = False


class DreamMotif(BaseModel):
    id: str
    matched_keywords: list[str]
    theme: str
    reflection_questions: list[str]


class DreamOutput(BaseModel):
    motifs: list[DreamMotif]
    emotional_tone: list[str]
    recurring: bool
    summary_themes: list[str]
    unmatched: bool
    method_notes: list[str]


def calculate_dream(request: DreamInput) -> DreamOutput:
    text = request.dream.casefold()
    motifs: list[DreamMotif] = []
    for entry in MOTIFS:
        matched = [word for word in entry["keywords"] if str(word).casefold() in text]
        if matched:
            motifs.append(
                DreamMotif(
                    id=str(entry["id"]),
                    matched_keywords=[str(word) for word in matched],
                    theme=str(entry["theme"]),
                    reflection_questions=[str(item) for item in entry["questions"]],
                )
            )
    themes = [item.theme for item in motifs]
    if request.recurring:
        themes.append("重复梦提示持续关注同一压力、需要或未完成事件")
    emotion_counts = Counter(item.strip() for item in request.emotions if item.strip())
    emotional_tone = [item for item, _ in emotion_counts.most_common()]
    return DreamOutput(
        motifs=motifs,
        emotional_tone=emotional_tone,
        recurring=request.recurring,
        summary_themes=list(dict.fromkeys(themes))
        or ["暂未匹配固定象征，建议从情绪与最近事件入手"],
        unmatched=not motifs,
        method_notes=[
            "仅做仓库内置关键词与主题匹配，不调用语言模型。",
            "梦象没有唯一答案，反思问题比固定吉凶更重要。",
        ],
    )


@register_pipeline
class DreamPipeline(Pipeline[DreamInput, DreamOutput]):
    manifest = PipelineManifest(
        id="dream",
        name="梦象解析",
        version="0.1.0",
        ruleset="motif-reflection-v1",
        category="symbolic_reflection",
        tradition="cross_cultural",
        mode=PipelineMode.DETERMINISTIC,
        summary="离线匹配梦境母题、情绪与反思问题，不使用云端模型。",
        asset_pack="dream-v1",
        tags=["梦象", "母题", "反思"],
    )
    input_model = DreamInput
    output_model = DreamOutput

    def execute(
        self,
        request: DreamInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_dream(request),
            warnings=["梦境解析不是心理诊断；持续困扰请寻求合格专业人士帮助。"],
        )
