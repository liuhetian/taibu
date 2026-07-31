import pytest

from suanming.assets import (
    asset_references_for_pack,
    load_asset_manifest,
    verify_asset_manifest,
)
from suanming.errors import AssetManifestError
from suanming.runtime import describe_pipelines


def test_asset_manifest_and_checksums() -> None:
    manifest = load_asset_manifest()
    assert manifest["style"]["id"] == "celestial-archive-v1"
    verification = verify_asset_manifest()
    assert verification["ok"] is True
    assert len(verification["checks"]) == 17


def test_every_declared_pipeline_asset_pack_exists() -> None:
    manifest = load_asset_manifest()
    packs = {pack["id"]: pack for pack in manifest["packs"]}

    for pipeline in describe_pipelines():
        pack_id = pipeline["asset_pack"]
        if pack_id is not None:
            assert pack_id in packs
            assert pipeline["id"] in packs[pack_id]["pipelines"]


def test_unknown_asset_pack_is_rejected() -> None:
    with pytest.raises(AssetManifestError, match="missing-v1"):
        asset_references_for_pack("missing-v1", pipeline_id="test")
