from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .contracts import AssetReference
from .errors import AssetManifestError


def project_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).expanduser().resolve()
    configured = os.environ.get("SUANMING_PROJECT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    current = Path.cwd().resolve()
    if (current / "assets" / "manifest.json").is_file():
        return current
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "assets" / "manifest.json").is_file():
        return source_root
    bundled_root = Path(__file__).resolve().parent / "_bundle"
    if (bundled_root / "assets" / "manifest.json").is_file():
        return bundled_root
    raise AssetManifestError(
        "找不到 assets/manifest.json；请在项目根目录运行或设置 SUANMING_PROJECT_ROOT。"
    )


def load_asset_manifest(root: str | Path | None = None) -> dict[str, Any]:
    manifest_path = project_root(root) / "assets" / "manifest.json"
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AssetManifestError(f"无法读取素材清单：{manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise AssetManifestError(
            "素材清单不是有效 JSON。",
            details=[{"line": exc.lineno, "column": exc.colno, "message": exc.msg}],
        ) from exc
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise AssetManifestError("不支持的素材清单格式。")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_asset_manifest(root: str | Path | None = None) -> dict[str, Any]:
    base = project_root(root)
    manifest = load_asset_manifest(base)
    checks: list[dict[str, Any]] = []

    style = manifest.get("style", {})
    entries: list[tuple[str, dict[str, Any]]] = [("style", style)]
    for pack in manifest.get("packs", []):
        for asset in pack.get("assets", []):
            entries.append((str(pack.get("id", "unknown")), asset))

    for pack_id, asset in entries:
        relative = asset.get("path") or asset.get("anchor")
        expected = asset.get("sha256")
        if not relative:
            continue
        path = base / relative
        exists = path.is_file()
        actual = _sha256(path) if exists else None
        checks.append(
            {
                "pack": pack_id,
                "id": asset.get("id"),
                "path": str(relative).replace("\\", "/"),
                "exists": exists,
                "sha256": actual,
                "checksum_matches": bool(
                    exists and expected and actual.lower() == str(expected).lower()
                ),
            }
        )

    return {
        "schema_version": manifest["schema_version"],
        "ok": all(
            check["exists"] and check["checksum_matches"] for check in checks
        ),
        "checks": checks,
    }


def asset_references_for_pack(
    pack_id: str | None,
    *,
    pipeline_id: str,
    root: str | Path | None = None,
) -> list[AssetReference]:
    if not pack_id:
        return []
    manifest = load_asset_manifest(root)
    for pack in manifest.get("packs", []):
        if pack.get("id") != pack_id:
            continue
        references: list[AssetReference] = []
        for asset in pack.get("assets", []):
            pipelines = asset.get("pipelines")
            if pipelines and pipeline_id not in pipelines:
                continue
            references.append(
                AssetReference(
                    id=str(asset["id"]),
                    pack=pack_id,
                    role=str(asset["role"]),
                    path=str(asset["path"]),
                    media_type=str(asset.get("media_type", "image/png")),
                    status=str(asset.get("status", "available")),
                )
            )
        return references
    return []
