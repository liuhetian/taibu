from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ...contracts import (
    Pipeline,
    PipelineExecution,
    PipelineManifest,
    PipelineMode,
    RunContext,
)
from ...registry import register_pipeline_instance


class OracleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    draws: int = Field(default=1, ge=1, le=3)
    focus: Literal["general", "work", "relationship", "study", "travel", "wellbeing"] = "general"


class OracleLotDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(ge=1)
    title: str
    image: str
    verse: list[str] = Field(min_length=2, max_length=4)
    polarity: Literal["rising", "balanced", "cautious", "transforming"]
    themes: list[str]
    guidance: list[str]
    cautions: list[str]


class OraclePackDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    version: str
    ruleset: str
    tradition: str
    summary: str
    asset_pack: str
    asset_path: str
    attribution: str
    lots: list[OracleLotDefinition] = Field(min_length=8)


class OracleDraw(BaseModel):
    number: int
    title: str
    image: str
    verse: list[str]
    polarity: str
    themes: list[str]
    guidance: list[str]
    cautions: list[str]


class OracleOutput(BaseModel):
    oracle_id: str
    oracle_name: str
    question: str
    focus: str
    draws: list[OracleDraw]
    synthesis: list[str]
    provenance: str
    method_notes: list[str]


class ContentOraclePipeline(Pipeline[OracleInput, OracleOutput]):
    input_model = OracleInput
    output_model = OracleOutput

    def __init__(self, pack: OraclePackDefinition) -> None:
        self.pack = pack
        self.manifest = PipelineManifest(
            id=pack.id,
            name=pack.name,
            version=pack.version,
            ruleset=pack.ruleset,
            category="content_oracle",
            tradition=pack.tradition,
            mode=PipelineMode.SEEDED,
            summary=pack.summary,
            asset_pack=pack.asset_pack,
            tags=["原创签库", "可复现抽签", "数据驱动"],
        )

    def execute(self, request: OracleInput, context: RunContext) -> PipelineExecution:
        selected = context.rng.sample(self.pack.lots, k=request.draws)
        draws = [OracleDraw(**lot.model_dump()) for lot in selected]
        themes = list(dict.fromkeys(theme for lot in selected for theme in lot.themes))
        synthesis = [
            f"共同主题：{'、'.join(themes[:5])}。",
            "把签意改写成可验证的小行动，并为现实约束保留余地。",
        ]
        return PipelineExecution(
            result=OracleOutput(
                oracle_id=self.pack.id,
                oracle_name=self.pack.name,
                question=request.question,
                focus=request.focus,
                draws=draws,
                synthesis=synthesis,
                provenance=self.pack.attribution,
                method_notes=[
                    "由带种子的伪随机生成器无放回抽取；相同 seed 与输入可复现。",
                    "签文、题名与意象全部为本仓库原创内容，不冒充古籍原签或宗教神谕。",
                    "新增同类管线只需加入一个通过校验的 JSON 签库，无需修改 CLI。",
                ],
            ),
            warnings=["抽签用于文化创作与自我反思，不代表宗教机构、祖师或神明发言。"],
        )


def _load_packs() -> None:
    pack_dir = Path(__file__).resolve().parents[2] / "oracle_packs"
    for path in sorted(pack_dir.glob("*.json")):
        pack = OraclePackDefinition.model_validate_json(path.read_text(encoding="utf-8"))
        register_pipeline_instance(ContentOraclePipeline(pack))


_load_packs()
