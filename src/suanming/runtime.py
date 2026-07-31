from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime
from random import Random
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError

from .assets import asset_references_for_pack
from .contracts import (
    PipelineIdentity,
    PipelineMode,
    Reproducibility,
    ResultEnvelope,
    RunContext,
)
from .errors import AssetManifestError, InputValidationError
from .registry import get_pipeline, iter_pipelines
from .shared.time import localize_datetime


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _seeded_random(seed: str) -> Random:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return Random(int.from_bytes(digest, "big"))


def _effective_datetime(request: dict[str, Any], now: datetime) -> tuple[datetime, str]:
    timezone_name = str(request.get("timezone") or "Asia/Shanghai")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise InputValidationError(
            f"未知时区：{timezone_name}",
            details=[{"field": "timezone", "type": "zoneinfo_not_found"}],
        ) from exc

    candidate = request.get("datetime")
    if candidate is None:
        return now.astimezone(timezone), timezone_name

    if isinstance(candidate, datetime):
        parsed = candidate
    else:
        try:
            parsed = datetime.fromisoformat(str(candidate))
        except ValueError as exc:
            raise InputValidationError(
                "datetime 必须是 ISO 8601 格式。",
                details=[{"field": "datetime", "value": candidate}],
            ) from exc

    try:
        parsed = localize_datetime(parsed, timezone_name)
    except ValueError as exc:
        raise InputValidationError(
            str(exc),
            details=[{"field": "datetime", "value": str(candidate)}],
        ) from exc
    return parsed, timezone_name


def describe_pipelines() -> list[dict[str, Any]]:
    return [
        {
            **pipeline.manifest.model_dump(mode="json"),
            "input_schema": f"suanming schema {pipeline.manifest.id} --kind input",
            "output_schema": f"suanming schema {pipeline.manifest.id} --kind output",
        }
        for pipeline in iter_pipelines()
    ]


def pipeline_schema(pipeline_id: str, kind: str) -> dict[str, Any]:
    pipeline = get_pipeline(pipeline_id)
    if kind == "input":
        return pipeline.input_schema()
    if kind == "output":
        return pipeline.output_schema()
    return {
        "input": pipeline.input_schema(),
        "output": pipeline.output_schema(),
        "manifest": pipeline.manifest.model_dump(mode="json"),
    }


def run_pipeline(
    pipeline_id: str,
    raw_request: dict[str, Any],
    *,
    seed: str | None = None,
    locale: str = "zh-CN",
    now: datetime | None = None,
) -> ResultEnvelope:
    pipeline = get_pipeline(pipeline_id)
    try:
        request = pipeline.input_model.model_validate(raw_request)
    except ValidationError as exc:
        raise InputValidationError(
            "输入未通过管线校验。",
            details=[
                dict(item)
                for item in exc.errors(
                    include_url=False,
                    include_context=False,
                )
            ],
        ) from exc

    request_dict = request.model_dump(mode="json", exclude_none=True)
    current_time = now or datetime.now(UTC)
    effective_datetime, timezone_name = _effective_datetime(request_dict, current_time)
    actual_seed = seed or (
        "deterministic"
        if pipeline.manifest.mode == PipelineMode.DETERMINISTIC
        else secrets.token_hex(16)
    )
    context = RunContext(
        seed=actual_seed,
        rng=_seeded_random(actual_seed),
        now=current_time,
        effective_datetime=effective_datetime,
        timezone=timezone_name,
        locale=locale,
    )
    execution = pipeline.execute(request, context)
    result = pipeline.output_model.model_validate(execution.result)
    assets = list(execution.assets)
    asset_warnings: list[str] = []
    try:
        declared_assets = asset_references_for_pack(
            pipeline.manifest.asset_pack,
            pipeline_id=pipeline.manifest.id,
        )
        existing_ids = {asset.id for asset in assets}
        assets.extend(asset for asset in declared_assets if asset.id not in existing_ids)
    except AssetManifestError:
        asset_warnings.append("素材清单不可用；计算结果不受影响。")

    run_basis = {
        "pipeline": pipeline.manifest.id,
        "version": pipeline.manifest.version,
        "ruleset": pipeline.manifest.ruleset,
        "request": request_dict,
        "seed": actual_seed,
        "result": result.model_dump(mode="json", exclude_none=True),
        "locale": locale,
    }
    run_id = hashlib.sha256(_canonical_json(run_basis).encode("utf-8")).hexdigest()[:24]

    manifest = pipeline.manifest
    return ResultEnvelope(
        pipeline=PipelineIdentity(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            ruleset=manifest.ruleset,
            category=manifest.category,
            tradition=manifest.tradition,
            mode=manifest.mode,
        ),
        request=request_dict,
        result=result.model_dump(mode="json", exclude_none=True),
        assets=assets,
        reproducibility=Reproducibility(
            run_id=run_id,
            seed=actual_seed,
            effective_datetime=effective_datetime,
            timezone=timezone_name,
            locale=locale,
        ),
        warnings=execution.warnings + asset_warnings,
        notes=execution.notes,
    )
