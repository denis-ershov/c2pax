"""Общие фикстуры и генераторы тестовых данных для c2pax tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from c2pax.backend.mock import MockC2paBackend


@pytest.fixture
def ec_keypair() -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate, str, str]:
    """Генерирует пару EC-ключ и самоподписанный X.509 сертификат для тестов."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "c2pax Test Studio"),
            x509.NameAttribute(NameOID.COMMON_NAME, "c2pax Test Signer"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(private_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    return private_key, cert, cert_pem, key_pem


@pytest.fixture
def expired_ec_keypair() -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate, str, str]:
    """Генерирует пару EC-ключ и просроченный X.509 сертификат."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Expired Signer"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=30))
        .not_valid_after(datetime.now(timezone.utc) - timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    return private_key, cert, cert_pem, key_pem


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Возвращает минимальный валидный JPEG-заголовок (1x1 px)."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
    )


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Возвращает минимальный валидный PNG (1x1 px)."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
        b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def mock_backend() -> MockC2paBackend:
    """Создает изолированный mock-бэкенд для тестирования."""
    return MockC2paBackend()


@pytest.fixture
def sample_c2pa_manifest_data(ec_keypair: tuple[Any, Any, str, str]) -> dict[str, Any]:
    """Возвращает реалистичную структуру манифест-стора C2PA."""
    _, _, cert_pem, _ = ec_keypair
    return {
        "active_manifest": "urn:c2pa:manifest_123",
        "manifests": {
            "urn:c2pa:manifest_123": {
                "title": "Sunset Landscape",
                "format": "image/jpeg",
                "claim_generator": "c2pax Test Suite 1.0",
                "signature_info": {
                    "issuer": "c2pax Test Signer",
                    "cert_serial_number": "1234567890",
                    "time": "2026-08-17T12:00:00Z",
                    "cert": cert_pem,
                },
                "assertions": [
                    {
                        "label": "c2pa.actions",
                        "data": {
                            "actions": [
                                {
                                    "action": "c2pa.created",
                                    "softwareAgent": "c2pax Generator",
                                    "when": "2026-08-17T11:00:00Z",
                                    "parameters": {"tool": "UnitTest"},
                                }
                            ]
                        },
                    },
                    {
                        "label": "c2pa.ai_generative",
                        "data": {
                            "tool": "Midjourney v6",
                            "model": "MJ-v6",
                            "prompt": "Sunset over mountain landscape",
                        },
                    },
                    {
                        "label": "c2pa.data_mining",
                        "data": {
                            "entries": {
                                "c2pa.data_mining": {"use": "notAllowed"},
                                "c2pa.ai_generative_training": {"use": "notAllowed"},
                            }
                        },
                    },
                ],
                "ingredients": [
                    {
                        "title": "Raw Sketch.png",
                        "format": "image/png",
                        "relationship": "parentOf",
                        "instance_id": "urn:c2pa:ing_1",
                    }
                ],
            }
        },
    }
