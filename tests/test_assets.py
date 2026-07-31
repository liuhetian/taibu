from suanming.assets import load_asset_manifest, verify_asset_manifest


def test_asset_manifest_and_checksums() -> None:
    manifest = load_asset_manifest()
    assert manifest["style"]["id"] == "celestial-archive-v1"
    verification = verify_asset_manifest()
    assert verification["ok"] is True
    assert len(verification["checks"]) == 17
