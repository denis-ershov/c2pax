"""Утилиты для парсинга и анализа X.509 сертификатов стандарта C2PA."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID

from c2pax.core.exceptions import CertificateError
from c2pax.core.models import IdentityInfo


def parse_pem_certificates(pem_data: str | bytes) -> list[x509.Certificate]:
    """Парсит один или несколько PEM сертификатов из строки или байтов."""
    if isinstance(pem_data, str):
        data = pem_data.encode("utf-8")
    else:
        data = pem_data

    certs: list[x509.Certificate] = []
    try:
        # Пробуем загрузить как цепочку / множественные сертификаты
        certs = x509.load_pem_x509_certificates(data)
    except Exception:
        try:
            # Одиночный сертификат
            cert = x509.load_pem_x509_certificate(data)
            certs = [cert]
        except Exception as e:
            raise CertificateError(f"Не удалось распарсить PEM сертификат: {e}") from e

    if not certs:
        raise CertificateError("PEM данные не содержат валидных X.509 сертификатов")
    return certs


def get_cert_fingerprint(cert: x509.Certificate) -> str:
    """Возвращает SHA-256 отпечаток сертификата в шестнадцатеричном виде."""
    return cert.fingerprint(hashes.SHA256()).hex()


def extract_identity_from_cert(cert: x509.Certificate) -> IdentityInfo:
    """Извлекает нормализованные данные о субъекте и эмитенте из X.509 сертификата."""
    subject_cn = None
    subject_o = None
    subject_c = None
    issuer_cn = None
    issuer_o = None

    for attr in cert.subject:
        if attr.oid == NameOID.COMMON_NAME:
            subject_cn = str(attr.value)
        elif attr.oid == NameOID.ORGANIZATION_NAME:
            subject_o = str(attr.value)
        elif attr.oid == NameOID.COUNTRY_NAME:
            subject_c = str(attr.value)

    for attr in cert.issuer:
        if attr.oid == NameOID.COMMON_NAME:
            issuer_cn = str(attr.value)
        elif attr.oid == NameOID.ORGANIZATION_NAME:
            issuer_o = str(attr.value)

    issuer_str = issuer_cn or issuer_o or "Unknown Issuer"
    if issuer_cn and issuer_o and issuer_cn != issuer_o:
        issuer_str = f"{issuer_cn} ({issuer_o})"

    serial_hex = f"{cert.serial_number:X}"

    raw_summary: dict[str, Any] = {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": serial_hex,
        "not_valid_before": cert.not_valid_before_utc.isoformat(),
        "not_valid_after": cert.not_valid_after_utc.isoformat(),
        "fingerprint_sha256": get_cert_fingerprint(cert),
    }

    return IdentityInfo(
        signer_name=subject_cn or subject_o or "Unknown Signer",
        organization=subject_o,
        cert_issuer=issuer_str,
        cert_serial=serial_hex,
        country=subject_c,
        raw_x509_summary=raw_summary,
    )


def is_certificate_expired(
    cert: x509.Certificate,
    reference_time: datetime | None = None,
) -> bool:
    """Проверяет, истек ли срок действия сертификата на указанную дату."""
    check_time = reference_time or datetime.now(timezone.utc)
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=timezone.utc)

    return check_time < cert.not_valid_before_utc or check_time > cert.not_valid_after_utc
