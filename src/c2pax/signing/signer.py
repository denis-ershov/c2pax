"""Модель подписанта цифровых манифестов C2PA (Signer) с безопасным хранением ключей."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from c2pax.core.exceptions import CertificateError, KeyPairMismatchError
from c2pax.verification.cert_utils import parse_pem_certificates


@dataclass(slots=True)
class Signer:
    """Конфигурация цифрового подписанта стандарта C2PA.

    В целях безопасности закрытый ключ маскируется в строковых представлениях (__repr__, __str__).
    """

    certificate_pem: str
    private_key_pem: str = field(repr=False)
    alg: str = "es256"
    tsa_url: str | None = None
    private_key_password: str | bytes | None = field(default=None, repr=False)

    def __repr__(self) -> str:
        cert_preview = self.certificate_pem[:30].replace("\n", "") if self.certificate_pem else ""
        return (
            f"Signer(certificate_pem='{cert_preview}...', "
            f"private_key_pem='***REDACTED***', alg='{self.alg}', tsa_url={self.tsa_url!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def from_pem(
        cls,
        certificate: str | Path,
        private_key: str | Path,
        alg: str = "es256",
        tsa_url: str | None = None,
        private_key_password: str | bytes | None = None,
    ) -> Signer:
        """Создает Signer из путей к PEM-файлам или строкового содержимого."""
        cert_content = ""
        if isinstance(certificate, str) and "-----BEGIN CERTIFICATE-----" in certificate:
            cert_content = certificate
        else:
            try:
                p = Path(certificate)
                if p.is_file():
                    cert_content = p.read_text(encoding="utf-8")
                else:
                    raise CertificateError(f"Файл сертификата не найден: {certificate}")
            except OSError as e:
                raise CertificateError(f"Файл сертификата не найден: {certificate}") from e

        key_content = ""
        if (
            isinstance(private_key, str)
            and "-----BEGIN" in private_key
            and "KEY-----" in private_key
        ):
            key_content = private_key
        else:
            try:
                p = Path(private_key)
                if p.is_file():
                    key_content = p.read_text(encoding="utf-8")
                else:
                    raise CertificateError(f"Файл закрытого ключа не найден: {private_key}")
            except OSError as e:
                raise CertificateError(f"Файл закрытого ключа не найден: {private_key}") from e

        signer = cls(
            certificate_pem=cert_content,
            private_key_pem=key_content,
            alg=alg.lower(),
            tsa_url=tsa_url,
            private_key_password=private_key_password,
        )
        signer.validate_keypair()
        return signer

    def validate_keypair(self) -> None:
        """Проверяет криптографическое соответствие сертификата и закрытого ключа."""
        try:
            certs = parse_pem_certificates(self.certificate_pem)
            if not certs:
                raise CertificateError("Сертификат подписанта не содержит валидных записей")
            cert = certs[0]

            pwd_bytes = (
                self.private_key_password.encode("utf-8")
                if isinstance(self.private_key_password, str)
                else self.private_key_password
            )

            key = serialization.load_pem_private_key(
                self.private_key_pem.encode("utf-8"),
                password=pwd_bytes,
            )

            # Сравниваем открытые ключи из сертификата и приватного ключа
            cert_public_bytes = cert.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            key_public_bytes = key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            if cert_public_bytes != key_public_bytes:
                raise KeyPairMismatchError(
                    "Открытый ключ сертификата не совпадает с предоставленным закрытым ключом!"
                )
        except KeyPairMismatchError:
            raise
        except Exception as e:
            raise CertificateError(f"Ошибка проверки пары сертификат-ключ: {e}") from e
