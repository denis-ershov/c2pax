"""Интеграционные тесты c2pax.inspect."""

from pathlib import Path
from typing import Any

from c2pax.api import inspect
from c2pax.backend.mock import MockC2paBackend


def test_inspect_unsigned_asset(tmp_path: Path, sample_jpeg_bytes: bytes) -> None:
    img_file = tmp_path / "unsigned.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    info = inspect(img_file, backend=backend)

    assert info.has_c2pa is False
    assert info.manifest_status.present is False
    assert info.metadata.format == "image/jpeg"
    assert info.metadata.file_size_bytes == len(sample_jpeg_bytes)
    assert info.provenance is None


def test_inspect_signed_c2pa_asset(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    img_file = tmp_path / "signed.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(img_file), sample_c2pa_manifest_data)

    info = inspect(img_file, backend=backend)

    assert info.has_c2pa is True
    assert info.manifest_status.present is True
    assert info.manifest_status.claim_generator == "c2pax Test Suite 1.0"
    assert info.metadata.title == "Sunset Landscape"

    assert info.identity.signer_name == "c2pax Test Signer"
    assert info.ai.generated is True
    assert "Midjourney v6" in info.ai.tools
    assert info.ai.prompts == ["Sunset over mountain landscape"]
    assert info.permissions.data_mining_allowed is False

    assert info.provenance is not None
    assert info.provenance.root.title == "Sunset Landscape"
    assert len(info.provenance.actions) == 1
    assert info.provenance.actions[0].name == "c2pa.created"
