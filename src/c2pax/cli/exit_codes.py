"""Коды возврата CLI c2pax."""

from __future__ import annotations

EXIT_VALID = 0  # Все проверки пройдены (VALID)
EXIT_INVALID = 1  # Нарушена криптографическая целостность (INVALID)
EXIT_UNTRUSTED = 2  # Сертификат не входит в TrustStore (UNTRUSTED)
EXIT_NO_MANIFEST = 3  # Манифест C2PA отсутствует (NO_MANIFEST)
EXIT_ERROR = 4  # Неподдерживаемый формат или ошибка исполнения (UNSUPPORTED / ERROR)
