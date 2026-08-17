"""Тесты локального хранилища доверенных сертификатов TrustStore."""

from pathlib import Path
from typing import Any

import pytest

from c2pax.core.exceptions import CertificateError
from c2pax.verification.trust import TrustStore


def test_trust_store_from_pem(ec_keypair: tuple[Any, Any, str, str]) -> None:
    _, cert, cert_pem, _ = ec_keypair
    store = TrustStore.from_pem(cert_pem)
    assert store.get_signers_count() == 1
    assert store.is_signer_trusted(cert) is True
    assert store.is_signer_trusted(cert_pem) is True


def test_trust_store_from_file(tmp_path: Path, ec_keypair: tuple[Any, Any, str, str]) -> None:
    _, cert, cert_pem, _ = ec_keypair
    pem_file = tmp_path / "signer.pem"
    pem_file.write_text(cert_pem, encoding="utf-8")

    store = TrustStore.from_pem(pem_file)
    assert store.is_signer_trusted(cert) is True


def test_trust_store_from_directory(tmp_path: Path, ec_keypair: tuple[Any, Any, str, str]) -> None:
    _, cert, cert_pem, _ = ec_keypair
    certs_dir = tmp_path / "trusted_certs"
    certs_dir.mkdir()
    (certs_dir / "root.crt").write_text(cert_pem, encoding="utf-8")

    store = TrustStore.from_directory(certs_dir)
    assert store.is_signer_trusted(cert) is True


def test_trust_store_untrusted(
    ec_keypair: tuple[Any, Any, str, str],
    expired_ec_keypair: tuple[Any, Any, str, str],
) -> None:
    _, cert1, cert_pem1, _ = ec_keypair
    _, cert2, _, _ = expired_ec_keypair

    store = TrustStore.from_pem(cert_pem1)
    assert store.is_signer_trusted(cert1) is True
    assert store.is_signer_trusted(cert2) is False


def test_trust_store_invalid_pem() -> None:
    with pytest.raises(CertificateError):
        TrustStore.from_pem("INVALID NOT A CERT DATA")
