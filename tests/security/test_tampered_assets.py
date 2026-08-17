"""Тесты безопасности и верификации поддельных / поврежденных ассетов."""

from pathlib import Path
from typing import Any

from c2pax.api import verify
from c2pax.backend.mock import MockC2paBackend
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.status import VerificationStatus
from c2pax.verification.trust import TrustStore


def test_tampered_content_hash(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    """Тест: при модификации пикселей контента хэш не сходится -> INVALID."""
    img_file = tmp_path / "tampered.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    # Симулируем ошибку сверки хэшей от c2pa engine
    backend.set_mock_manifest(
        str(img_file),
        sample_c2pa_manifest_data,
        validation_status=[
            {"code": "hash.mismatch", "message": "Content hash does not match assertion"}
        ],
    )

    res = verify(img_file, policy=VerificationPolicy.permissive(), backend=backend)
    assert res.status == VerificationStatus.INVALID
    assert res.valid is False
    assert res.integrity.content_hash_matches is False
    assert any(err.code == "hash.mismatch" for err in res.errors)


def test_tampered_signature(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    """Тест: поврежденная цифровая подпись клейма -> INVALID."""
    img_file = tmp_path / "bad_sig.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(
        str(img_file),
        sample_c2pa_manifest_data,
        validation_status=[
            {
                "code": "claimSignature.invalid",
                "message": "Cryptographic signature validation failed",
            }
        ],
    )

    res = verify(img_file, policy=VerificationPolicy.permissive(), backend=backend)
    assert res.status == VerificationStatus.INVALID
    assert res.valid is False
    assert res.integrity.signature_valid is False


def test_expired_certificate_strict_policy(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
    expired_ec_keypair: tuple[Any, Any, str, str],
) -> None:
    """Тест: просроченный сертификат при политике standard / strict бракуется."""
    _, _, expired_cert_pem, _ = expired_ec_keypair
    # Подменяем сертификат в манифесте на просроченный
    manifest_data = sample_c2pa_manifest_data.copy()
    manifest_data["manifests"]["urn:c2pa:manifest_123"]["signature_info"]["cert"] = expired_cert_pem

    img_file = tmp_path / "expired.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    backend.set_mock_manifest(str(img_file), manifest_data)

    trust_store = TrustStore.from_pem(expired_cert_pem)

    res = verify(
        img_file,
        policy=VerificationPolicy.standard(),
        trust_store=trust_store,
        backend=backend,
    )
    assert res.status == VerificationStatus.INVALID
    assert res.valid is False
    assert res.trust.cert_expired is True
