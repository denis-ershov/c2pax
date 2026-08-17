"""Иерархия исключений c2pax SDK."""

from __future__ import annotations


class C2PAError(Exception):
    """Базовое исключение для всех ошибок c2pax."""


class AssetError(C2PAError):
    """Ошибки, связанные с доступом или форматом ассета."""


class AssetNotFoundError(AssetError, FileNotFoundError):
    """Файл ассета не найден."""


class UnsupportedFormatError(AssetError):
    """Неподдерживаемый медиа-формат или расширение файла."""


class AssetIOError(AssetError):
    """Ошибка ввода-вывода при чтении или записи ассета."""


class ManifestError(C2PAError):
    """Ошибки, связанные с чтением или структурой C2PA манифеста."""


class ManifestNotFoundError(ManifestError):
    """C2PA манифест отсутствует в указанном ассете."""


class CorruptedManifestError(ManifestError):
    """C2PA манифест поврежден или не может быть десериализован."""


class CyclicProvenanceError(ManifestError):
    """Обнаружен недопустимый цикл в графе происхождения (DAG)."""


class VerificationError(C2PAError):
    """Ошибки при верификации цифрового манифеста."""


class IntegrityError(VerificationError):
    """Нарушена криптографическая целостность (хэши контента или подпись повреждены)."""


class UntrustedSignerError(VerificationError):
    """Сертификат подписанта не входит в список доверенных (TrustStore)."""


class PolicyViolationError(VerificationError):
    """Результат проверки не соответствует заданной VerificationPolicy."""


class SigningError(C2PAError):
    """Ошибки в процессе создания манифеста и наложения цифровой подписи."""


class KeyPairMismatchError(SigningError):
    """Закрытый ключ не соответствует предоставленному сертификату."""


class CertificateError(SigningError):
    """Ошибка парсинга или недопустимый формат X.509 сертификата."""
