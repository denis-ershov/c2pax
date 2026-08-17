"""Тесты пакетной обработки verify_many и verify_directory."""

from pathlib import Path
from typing import Any

from c2pax.backend.mock import MockC2paBackend
from c2pax.integrations.batch import verify_directory, verify_many
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.status import VerificationStatus


def test_verify_many(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_png_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    f1 = tmp_path / "img1.jpg"
    f2 = tmp_path / "img2.png"
    f1.write_bytes(sample_jpeg_bytes)
    f2.write_bytes(sample_png_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(f1), sample_c2pa_manifest_data)

    results = verify_many(
        [f1, f2],
        policy=VerificationPolicy.permissive(),
        max_workers=2,
        backend=backend,
    )

    assert len(results) == 2
    assert results[0].status == VerificationStatus.VALID
    assert results[1].status == VerificationStatus.NO_MANIFEST


def test_verify_directory(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_png_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    sub_dir = tmp_path / "gallery"
    sub_dir.mkdir()
    f1 = sub_dir / "photo1.jpg"
    f2 = sub_dir / "photo2.png"
    f1.write_bytes(sample_jpeg_bytes)
    f2.write_bytes(sample_png_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(f1), sample_c2pa_manifest_data)

    results_dict = verify_directory(
        sub_dir,
        recursive=True,
        policy=VerificationPolicy.permissive(),
        backend=backend,
    )

    assert len(results_dict) == 2
    assert results_dict[f1].status == VerificationStatus.VALID
    assert results_dict[f2].status == VerificationStatus.NO_MANIFEST
