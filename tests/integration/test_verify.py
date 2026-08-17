"""Интеграционные тесты c2pax.verify."""

from pathlib import Path
from typing import Any

from c2pax.api import verify
from c2pax.backend.mock import MockC2paBackend
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.status import VerificationStatus
from c2pax.verification.trust import TrustStore


def test_verify_no_manifest(tmp_path: Path, sample_jpeg_bytes: bytes) -> None:
    img_file = tmp_path / "plain.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    res = verify(img_file, backend=backend)

    assert res.status == VerificationStatus.NO_MANIFEST
    assert res.valid is False


def test_verify_valid_with_permissive_policy(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    img_file = tmp_path / "signed.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(img_file), sample_c2pa_manifest_data)

    res = verify(
        img_file,
        policy=VerificationPolicy.permissive(),
        backend=backend,
    )

    assert res.status == VerificationStatus.VALID
    assert res.valid is True
    assert res.integrity.content_hash_matches is True
    assert res.integrity.signature_valid is True


def test_verify_untrusted_with_standard_policy(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    """При стандартной политике без добавления сертификата в TrustStore статус должен быть UNTRUSTED."""
    img_file = tmp_path / "signed.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(img_file), sample_c2pa_manifest_data)

    empty_trust_store = TrustStore()
    res = verify(
        img_file,
        policy=VerificationPolicy.standard(),
        trust_store=empty_trust_store,
        backend=backend,
    )

    assert res.status == VerificationStatus.UNTRUSTED
    assert res.valid is False
    assert res.trust.signer_in_trust_store is False


def test_verify_valid_with_trust_store(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
    ec_keypair: tuple[Any, Any, str, str],
) -> None:
    """При наличии сертификата в TrustStore статус VALID."""
    _, _, cert_pem, _ = ec_keypair
    img_file = tmp_path / "signed.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(img_file), sample_c2pa_manifest_data)

    trust_store = TrustStore.from_pem(cert_pem)
    res = verify(
        img_file,
        policy=VerificationPolicy.standard(),
        trust_store=trust_store,
        backend=backend,
    )

    assert res.status == VerificationStatus.VALID
    assert res.valid is True
    assert res.trust.signer_in_trust_store is True
