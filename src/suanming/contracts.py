from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from random import Random
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class PipelineMode(StrEnum):
    DETERMINISTIC = "deterministic"
    SEEDED = "seeded"
    HYBRID = "hybrid"
    ASSESSMENT = "assessment"


class AssetReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    pack: str
    role: str
    path: str | None = None
    media_type: str = "image/webp"
    status: str = "available"


class PipelineManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
    name: str
    version: str
    ruleset: str
    category: str
    tradition: str
    mode: PipelineMode
    summary: str
    asset_pack: str | None = None
    tags: list[str] = Field(default_factory=list)


class PipelineExecution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: BaseModel
    assets: list[AssetReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PipelineIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    version: str
    ruleset: str
    category: str
    tradition: str
    mode: PipelineMode


class Reproducibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    seed: str
    effective_datetime: datetime
    timezone: str
    locale: str


class ResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    pipeline: PipelineIdentity
    request: dict[str, Any]
    result: dict[str, Any]
    assets: list[AssetReference] = Field(default_factory=list)
    reproducibility: Reproducibility
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = "本结果用于传统文化研究与娱乐，不构成医疗、法律、财务或其他专业建议。"


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class RunContext:
    seed: str
    rng: Random
    now: datetime
    effective_datetime: datetime
    timezone: str
    locale: str


class Pipeline(ABC, Generic[InputT, OutputT]):
    manifest: PipelineManifest
    input_model: ClassVar[type[InputT]]
    output_model: ClassVar[type[OutputT]]

    @abstractmethod
    def execute(self, request: InputT, context: RunContext) -> PipelineExecution:
        """Execute one pure pipeline run."""

    @classmethod
    def input_schema(cls) -> dict[str, Any]:
        return cls.input_model.model_json_schema()

    @classmethod
    def output_schema(cls) -> dict[str, Any]:
        return cls.output_model.model_json_schema()
