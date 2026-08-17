"""Слой взаимодействия с C2PA движками."""

from c2pax.backend.base import BaseC2paBackend
from c2pax.backend.c2pa_rs import C2paRsBackend
from c2pax.backend.mock import MockC2paBackend

# Глобальный реестр текущего активного бэкенда
_DEFAULT_BACKEND: BaseC2paBackend | None = None


def get_default_backend() -> BaseC2paBackend:
    """Возвращает текущий активный C2PA бэкенд (по умолчанию C2paRsBackend с fallback на Mock при ошибке инициализации)."""
    global _DEFAULT_BACKEND
    if _DEFAULT_BACKEND is None:
        try:
            _DEFAULT_BACKEND = C2paRsBackend()
        except Exception:
            _DEFAULT_BACKEND = MockC2paBackend()
    return _DEFAULT_BACKEND


def set_default_backend(backend: BaseC2paBackend) -> None:
    """Устанавливает глобальный бэкенд C2PA."""
    global _DEFAULT_BACKEND
    _DEFAULT_BACKEND = backend


__all__ = [
    "BaseC2paBackend",
    "C2paRsBackend",
    "MockC2paBackend",
    "get_default_backend",
    "set_default_backend",
]
