from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ..ziwei import FOUR_TRANSFORMATIONS, ZiweiInput, calculate_ziwei


class ZiweiFlyingInput(ZiweiInput):
    model_config = ConfigDict(extra="forbid")


class FlyingTransformation(BaseModel):
    source_palace: str
    source_stem: str
    transformation: str
    star: str
    target_palace: str | None
    target_branch: str | None
    self_transformation: bool
    status: str


class ZiweiFlyingOutput(BaseModel):
    birth_year_transformations: dict[str, str]
    flights: list[FlyingTransformation]
    self_transformations: list[FlyingTransformation]
    unresolved_auxiliary_stars: list[str]
    method_notes: list[str]


def calculate_flying(request: ZiweiFlyingInput) -> ZiweiFlyingOutput:
    natal = calculate_ziwei(ZiweiInput.model_validate(request.model_dump()))
    star_locations = {
        star.name: palace
        for palace in natal.palaces
        for star in palace.stars
    }
    flights: list[FlyingTransformation] = []
    unresolved: set[str] = set()
    for source in natal.palaces:
        transformations = FOUR_TRANSFORMATIONS[source.stem]
        for transformation, star_name in transformations.items():
            target = star_locations.get(star_name)
            if target is None:
                unresolved.add(star_name)
            flights.append(
                FlyingTransformation(
                    source_palace=source.name,
                    source_stem=source.stem,
                    transformation=transformation,
                    star=star_name,
                    target_palace=target.name if target else None,
                    target_branch=target.branch if target else None,
                    self_transformation=bool(target and target.name == source.name),
                    status="resolved" if target else "star_not_in_foundation_chart",
                )
            )
    self_transforms = [flight for flight in flights if flight.self_transformation]
    return ZiweiFlyingOutput(
        birth_year_transformations=natal.transformations,
        flights=flights,
        self_transformations=self_transforms,
        unresolved_auxiliary_stars=sorted(unresolved),
        method_notes=[
            "以十二宫宫干分别引出生年四化表，并查找化星在本命盘的落宫。",
            "飞入本宫标记为 self_transformation；其余记录来源宫与目标宫。",
            "基础命盘未安置的辅曜会明确标为 unresolved，而不是虚构落宫。",
        ],
    )


@register_pipeline
class ZiweiFlyingPipeline(Pipeline[ZiweiFlyingInput, ZiweiFlyingOutput]):
    manifest = PipelineManifest(
        id="ziwei_flying_star",
        name="紫微飞星",
        version="0.1.0",
        ruleset="palace-stem-four-transformations-v1",
        category="natal_chart_analysis",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="由十二宫宫干引出四化，追踪化禄、化权、化科、化忌的来源与落宫。",
        asset_pack="ziwei-v1",
        tags=["飞化", "宫干四化", "自化", "落宫"],
    )
    input_model = ZiweiFlyingInput
    output_model = ZiweiFlyingOutput

    def execute(
        self,
        request: ZiweiFlyingInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(result=calculate_flying(request))
