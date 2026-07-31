from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterator

from .contracts import Pipeline
from .errors import UnknownPipelineError

_PIPELINES: dict[str, Pipeline] = {}
_DISCOVERED = False


def register_pipeline_instance(instance: Pipeline) -> Pipeline:
    pipeline_id = instance.manifest.id
    if pipeline_id in _PIPELINES:
        raise RuntimeError(f"Duplicate pipeline id: {pipeline_id}")
    _PIPELINES[pipeline_id] = instance
    return instance


def register_pipeline(pipeline_type: type[Pipeline]) -> type[Pipeline]:
    register_pipeline_instance(pipeline_type())
    return pipeline_type


def discover_pipelines() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return

    package = importlib.import_module("suanming.pipelines")
    for module in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if module.name.rsplit(".", 1)[-1].startswith("_"):
            continue
        importlib.import_module(module.name)
    _DISCOVERED = True


def iter_pipelines() -> Iterator[Pipeline]:
    discover_pipelines()
    for pipeline_id in sorted(_PIPELINES):
        yield _PIPELINES[pipeline_id]


def get_pipeline(pipeline_id: str) -> Pipeline:
    discover_pipelines()
    try:
        return _PIPELINES[pipeline_id]
    except KeyError as exc:
        available = ", ".join(sorted(_PIPELINES))
        raise UnknownPipelineError(
            f"未知管线：{pipeline_id}",
            details=[{"available": available}],
        ) from exc
