"""Тесты доменных моделей c2pax.core.models."""

from datetime import datetime, timezone

from c2pax.core.models import (
    AIProvenance,
    AssetInfo,
    AssetMetadata,
    IdentityInfo,
    ManifestStatus,
    PermissionsInfo,
)


def test_asset_metadata_defaults() -> None:
    meta = AssetMetadata()
    assert meta.title is None
    assert meta.format is None
    assert meta.file_size_bytes is None
    assert meta.created_at is None

    dt = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    meta2 = AssetMetadata(title="Test", format="image/jpeg", file_size_bytes=1024, created_at=dt)
    d = meta2.to_dict()
    assert d["title"] == "Test"
    assert d["format"] == "image/jpeg"
    assert d["file_size_bytes"] == 1024
    assert d["created_at"] == "2026-08-17T12:00:00+00:00"


def test_identity_info() -> None:
    ident = IdentityInfo(
        signer_name="Artist Name",
        organization="Art Studio",
        cert_issuer="Cert Authority",
        cert_serial="12345",
    )
    d = ident.to_dict()
    assert d["signer_name"] == "Artist Name"
    assert d["organization"] == "Art Studio"
    assert d["cert_issuer"] == "Cert Authority"
    assert d["cert_serial"] == "12345"


def test_ai_provenance() -> None:
    ai = AIProvenance(
        generated=True,
        assisted=False,
        tools=["Midjourney", "Photoshop"],
        prompts=["Cyberpunk car"],
    )
    d = ai.to_dict()
    assert d["generated"] is True
    assert d["assisted"] is False
    assert "Midjourney" in d["tools"]
    assert d["prompts"] == ["Cyberpunk car"]


def test_permissions_info() -> None:
    perm = PermissionsInfo(data_mining_allowed=False, ai_training_allowed=False)
    d = perm.to_dict()
    assert d["data_mining_allowed"] is False
    assert d["ai_training_allowed"] is False


def test_manifest_status() -> None:
    st = ManifestStatus(
        present=True, format_version="1.3", claim_generator="Photoshop", has_signature=True
    )
    d = st.to_dict()
    assert d["present"] is True
    assert d["claim_generator"] == "Photoshop"
    assert d["has_signature"] is True


def test_asset_info_aggregate() -> None:
    info = AssetInfo(
        has_c2pa=True,
        metadata=AssetMetadata(title="Full Test"),
        identity=IdentityInfo(signer_name="John Doe"),
        manifest_status=ManifestStatus(present=True),
    )
    d = info.to_dict()
    assert d["has_c2pa"] is True
    assert d["metadata"]["title"] == "Full Test"
    assert d["identity"]["signer_name"] == "John Doe"
    assert d["manifest_status"]["present"] is True
