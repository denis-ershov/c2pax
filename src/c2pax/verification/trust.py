"""Управление локальным хранилищем доверенных сертификатов (TrustStore)."""

from __future__ import annotations

from pathlib import Path

from cryptography import x509

from c2pax.core.exceptions import CertificateError
from c2pax.verification.cert_utils import (
    get_cert_fingerprint,
    parse_pem_certificates,
)


class TrustStore:
    """Локальное изолированное хранилище доверенных сертификатов C2PA."""

    def __init__(self) -> None:
        self._claim_signers: dict[str, x509.Certificate] = {}
        self._tsa_certs: dict[str, x509.Certificate] = {}
        self._root_cas: dict[str, x509.Certificate] = {}

    @classmethod
    def from_pem(cls, path_or_str: str | Path) -> TrustStore:
        """Создает TrustStore из PEM файла или строки с сертификатами."""
        store = cls()
        if isinstance(path_or_str, (str, Path)):
            path = Path(path_or_str)
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8")
                store.add_claim_signer_pem(content)
                return store
            if isinstance(path_or_str, str) and "-----BEGIN CERTIFICATE-----" in path_or_str:
                store.add_claim_signer_pem(path_or_str)
                return store

        raise CertificateError(f"Не удалось загрузить PEM сертификат: {path_or_str}")

    @classmethod
    def from_directory(cls, dir_path: str | Path) -> TrustStore:
        """Загружает все PEM/CRT сертификаты из указанной директории."""
        store = cls()
        directory = Path(dir_path)
        if not directory.exists() or not directory.is_dir():
            raise CertificateError(f"Каталог доверенных сертификатов не найден: {dir_path}")

        for ext in ("*.pem", "*.crt", "*.cer"):
            for cert_file in directory.glob(ext):
                try:
                    content = cert_file.read_text(encoding="utf-8")
                    store.add_claim_signer_pem(content)
                except Exception:
                    # Логируем или пропускаем поврежденные файлы
                    continue

        return store

    def add_claim_signer_pem(self, pem_data: str | bytes) -> None:
        """Добавляет доверенный сертификат подписанта (Claim Signer)."""
        certs = parse_pem_certificates(pem_data)
        for cert in certs:
            fp = get_cert_fingerprint(cert)
            self._claim_signers[fp] = cert
            # Также добавляем в список корневых, если self-signed
            if cert.issuer == cert.subject:
                self._root_cas[fp] = cert

    def add_tsa_pem(self, pem_data: str | bytes) -> None:
        """Добавляет доверенный сертификат службы меток времени (TSA)."""
        certs = parse_pem_certificates(pem_data)
        for cert in certs:
            fp = get_cert_fingerprint(cert)
            self._tsa_certs[fp] = cert

    def add_root_ca_pem(self, pem_data: str | bytes) -> None:
        """Добавляет корневой удостоверяющий центр (Root CA)."""
        certs = parse_pem_certificates(pem_data)
        for cert in certs:
            fp = get_cert_fingerprint(cert)
            self._root_cas[fp] = cert

    def is_signer_trusted(self, cert: x509.Certificate | bytes | str) -> bool:
        """Проверяет, является ли сертификат подписанта доверенным."""
        if not self._claim_signers and not self._root_cas:
            return False

        if isinstance(cert, (bytes, str)):
            try:
                certs = parse_pem_certificates(cert)
                if not certs:
                    return False
                target_cert = certs[0]
            except Exception:
                return False
        else:
            target_cert = cert

        fp = get_cert_fingerprint(target_cert)
        # 1. Прямое совпадение по отпечатку подписанта
        if fp in self._claim_signers:
            return True

        # 2. Проверка, выпущен ли сертификат доверенным CA
        for root in self._root_cas.values():
            if target_cert.issuer == root.subject:
                try:
                    target_cert.verify_directly_issued_by(root)
                    return True
                except Exception:
                    continue

        return False

    def is_tsa_trusted(self, cert: x509.Certificate | bytes | str) -> bool:
        """Проверяет, является ли сертификат TSA доверенным."""
        if not self._tsa_certs:
            return False

        if isinstance(cert, (bytes, str)):
            try:
                certs = parse_pem_certificates(cert)
                if not certs:
                    return False
                target_cert = certs[0]
            except Exception:
                return False
        else:
            target_cert = cert

        fp = get_cert_fingerprint(target_cert)
        return fp in self._tsa_certs

    def get_signers_count(self) -> int:
        """Возвращает количество зарегистрированных доверенных подписантов."""
        return len(self._claim_signers)
