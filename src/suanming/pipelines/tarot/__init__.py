from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ...contracts import (
    AssetReference,
    Pipeline,
    PipelineExecution,
    PipelineManifest,
    PipelineMode,
    RunContext,
)
from ...registry import register_pipeline
from .data import DECK, SPREADS, CardDefinition


SpreadName = Literal[
    "single",
    "three_card",
    "love",
    "celtic_cross",
    "horseshoe",
    "choice",
    "mind_body_spirit",
    "situation",
    "yes_no",
]


class TarotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spread: SpreadName = "single"
    question: str | None = Field(default=None, max_length=500)
    allow_reversed: bool = True
    reversal_rate: float = Field(default=0.5, ge=0, le=1)


class DrawnCard(BaseModel):
    position: str
    card_id: str
    name: str
    name_en: str
    arcana: str
    number: int
    suit: str | None
    element: str
    astrology: str | None
    orientation: Literal["upright", "reversed"]
    orientation_name: str
    keywords: list[str]
    reading: str
    asset_id: str


class TarotOutput(BaseModel):
    spread: str
    spread_name: str
    question: str | None
    cards: list[DrawnCard]
    element_balance: dict[str, int]
    major_arcana_count: int
    orientation_balance: dict[str, int]
    synthesis: list[str]
    yes_no: Literal["yes", "leaning_yes", "unclear", "leaning_no", "no"] | None
    method_notes: list[str]


SPREAD_NAMES = {
    "single": "单牌",
    "three_card": "三牌阵",
    "love": "爱情牌阵",
    "celtic_cross": "凯尔特十字",
    "horseshoe": "马蹄牌阵",
    "choice": "抉择牌阵",
    "mind_body_spirit": "身心灵牌阵",
    "situation": "情境牌阵",
    "yes_no": "是非牌阵",
}


def _drawn_card(
    definition: CardDefinition,
    position: str,
    reversed_: bool,
) -> DrawnCard:
    orientation = "reversed" if reversed_ else "upright"
    keywords = list(definition.reversed if reversed_ else definition.upright)
    orientation_name = "逆位" if reversed_ else "正位"
    return DrawnCard(
        position=position,
        card_id=definition.id,
        name=definition.name,
        name_en=definition.name_en,
        arcana=definition.arcana,
        number=definition.number,
        suit=definition.suit,
        element=definition.element,
        astrology=definition.astrology,
        orientation=orientation,
        orientation_name=orientation_name,
        keywords=keywords,
        reading=f"{position}落下{definition.name}{orientation_name}，核心线索为：{'、'.join(keywords)}。",
        asset_id=f"tarot.card.{definition.id}",
    )


def _yes_no(cards: list[tuple[CardDefinition, bool]]) -> str:
    score = sum((-card.base_tone if reversed_ else card.base_tone) for card, reversed_ in cards)
    if score >= 2:
        return "yes"
    if score == 1:
        return "leaning_yes"
    if score == 0:
        return "unclear"
    if score == -1:
        return "leaning_no"
    return "no"


def calculate_tarot(request: TarotInput, context: RunContext) -> TarotOutput:
    positions = SPREADS[request.spread]
    definitions = context.rng.sample(DECK, len(positions))
    chosen: list[tuple[CardDefinition, bool]] = []
    cards: list[DrawnCard] = []
    for position, definition in zip(positions, definitions, strict=True):
        reversed_ = (
            request.allow_reversed
            and context.rng.random() < request.reversal_rate
        )
        chosen.append((definition, reversed_))
        cards.append(_drawn_card(definition, position, reversed_))

    element_balance = Counter(card.element for card, _ in chosen)
    orientation_balance = Counter(
        "reversed" if reversed_ else "upright" for _, reversed_ in chosen
    )
    dominant_elements = [
        element
        for element, count in element_balance.items()
        if count == max(element_balance.values())
    ]
    synthesis = [
        f"元素重心：{'、'.join(sorted(dominant_elements))}。",
        f"大阿尔卡那出现 {sum(card.arcana == 'major' for card, _ in chosen)} 张。",
        (
            "正位较多，信息更偏向外显行动。"
            if orientation_balance["upright"] > orientation_balance["reversed"]
            else "逆位较多，信息更偏向内在调整。"
            if orientation_balance["reversed"] > orientation_balance["upright"]
            else "正逆位均衡，需要同时观察行动与内在动机。"
        ),
    ]
    return TarotOutput(
        spread=request.spread,
        spread_name=SPREAD_NAMES[request.spread],
        question=request.question,
        cards=cards,
        element_balance=dict(sorted(element_balance.items())),
        major_arcana_count=sum(card.arcana == "major" for card, _ in chosen),
        orientation_balance={
            "upright": orientation_balance["upright"],
            "reversed": orientation_balance["reversed"],
        },
        synthesis=synthesis,
        yes_no=_yes_no(chosen) if request.spread == "yes_no" else None,
        method_notes=[
            "完整牌库为 22 张大阿尔卡那与 56 张小阿尔卡那。",
            "抽牌采用结果信封中的 seed 驱动，可完全复现。",
            "关键词来自仓库内置结构化牌义，不调用外部解释服务。",
        ],
    )


@register_pipeline
class TarotPipeline(Pipeline[TarotInput, TarotOutput]):
    manifest = PipelineManifest(
        id="tarot",
        name="塔罗",
        version="0.1.0",
        ruleset="complete-deck-seeded-draw-v1",
        category="card_oracle",
        tradition="western_esoteric",
        mode=PipelineMode.SEEDED,
        summary="使用完整 78 张牌库与九种牌阵进行可复现抽牌，输出正逆位与结构化牌义。",
        asset_pack="tarot-v1",
        tags=["78张", "牌阵", "正逆位", "可复现"],
    )
    input_model = TarotInput
    output_model = TarotOutput

    def execute(
        self,
        request: TarotInput,
        context: RunContext,
    ) -> PipelineExecution:
        output = calculate_tarot(request, context)
        assets = [
            AssetReference(
                id="tarot.cover",
                pack="tarot-v1",
                role="pipeline-cover",
                path="assets/packs/tarot/cover.png",
                media_type="image/png",
                status="available",
            )
        ]
        return PipelineExecution(result=output, assets=assets)
