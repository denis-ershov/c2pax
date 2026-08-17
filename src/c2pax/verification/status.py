"""Статусы верификации C2PA."""

from __future__ import annotations

from enum import Enum


class VerificationStatus(str, Enum):
    """Итоговый статус верификации медиа-ассета и C2PA манифеста."""

    VALID = "valid"  # Все проверки политики пройдены успешно
    INVALID = (
        "invalid"  # Нарушена криптографическая целостность (хэш контента или подпись не сошлись)
    )
    UNTRUSTED = "untrusted"  # Подпись валидна, но сертификат не входит в TrustStore
    NO_MANIFEST = "no_manifest"  # Манифест C2PA отсутствует
    UNSUPPORTED = "unsupported"  # Формат файла или версия контейнера не поддерживается
    ERROR = "error"  # Ошибка парсинга или внутренняя ошибка выполнения
