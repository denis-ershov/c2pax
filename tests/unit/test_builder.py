"""Тесты Builder API и Signer c2pax.signing."""

from pathlib import Path
from typing import Any

import pytest

from c2pax.backend.mock import MockC2paBackend
from c2pax.core.exceptions import KeyPairMismatchError
from c2pax.signing.builder import Builder, sign
from c2pax.signing.signer import Signer


def test_signer_validation_success(ec_keypair: tuple[Any, Any, str, str]) -> None:
    _, _, cert_pem, key_pem = ec_keypair
    signer = Signer.from_pem(certificate=cert_pem, private_key=key_pem, alg="es256")
    assert signer.alg == "es256"


def test_signer_keypair_mismatch(
    ec_keypair: tuple[Any, Any, str, str],
    expired_ec_keypair: tuple[Any, Any, str, str],
) -> None:
    _, _, cert_pem1, _ = ec_keypair
    _, _, _, key_pem2 = expired_ec_keypair
    with pytest.raises(KeyPairMismatchError):
        Signer.from_pem(certificate=cert_pem1, private_key=key_pem2)


def test_builder_manifest_definition() -> None:
    builder = (
        Builder()
        .set_title("Marketing Banner")
        .set_format("image/jpeg")
        .set_claim_generator("c2pax CLI 1.0")
        .add_action("c2pa.created", software="c2pax")
        .add_ai_generation_assertion(tool="DALL-E 3", prompt="Futuristic city")
        .add_ai_training_permission(data_mining_allowed=False, ai_training_allowed=False)
    )

    definition = builder.build_manifest_definition()
    assert definition["title"] == "Marketing Banner"
    assert definition["format"] == "image/jpeg"
    assert definition["claim_generator"] == "c2pax CLI 1.0"
    assert len(definition["assertions"]) == 3


def test_builder_and_sign_with_mock_backend(
    tmp_path: Path,
    ec_keypair: tuple[Any, Any, str, str],
    sample_jpeg_bytes: bytes,
) -> None:
    _, _, cert_pem, key_pem = ec_keypair
    signer = Signer.from_pem(certificate=cert_pem, private_key=key_pem)

    input_file = tmp_path / "in.jpg"
    output_file = tmp_path / "out.jpg"
    input_file.write_bytes(sample_jpeg_bytes)

    backend = MockC2paBackend()
    manifest_bytes = sign(
        input_file=input_file,
        output_file=output_file,
        signer=signer,
        title="Quick Signed Image",
        creator="Mock Studio",
        ai_tool="Midjourney",
        backend=backend,
    )

    assert len(manifest_bytes) > 0
    assert output_file.exists()
    assert len(backend._signed_history) == 1
