"""Политики верификации C2PA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class VerificationPolicy:
    """Конфигурация политики верификации цифрового манифеста C2PA."""

    require_trusted_signer: bool = False
    require_timestamp: bool = False
    allow_expired_certs: bool = True
    fail_on_warnings: bool = False
    max_clock_skew_seconds: int = 300

    @classmethod
    def permissive(cls) -> VerificationPolicy:
        """Валидно, если сошлась криптография, независимо от наличия в TrustStore."""
        return cls(
            require_trusted_signer=False,
            require_timestamp=False,
            allow_expired_certs=True,
            fail_on_warnings=False,
        )

    @classmethod
    def standard(cls) -> VerificationPolicy:
        """Требует доверенного подписанта, но допускает отсутствие TSA-метки."""
        return cls(
            require_trusted_signer=True,
            require_timestamp=False,
            allow_expired_certs=False,
            fail_on_warnings=False,
        )

    @classmethod
    def strict(cls) -> VerificationPolicy:
        """Требует валидной доверенной подписи, доверенной TSA и отсутствия warnings."""
        return cls(
            require_trusted_signer=True,
            require_timestamp=True,
            allow_expired_certs=False,
            fail_on_warnings=True,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "require_trusted_signer": self.require_trusted_signer,
            "require_timestamp": self.require_timestamp,
            "allow_expired_certs": self.allow_expired_certs,
            "fail_on_warnings": self.fail_on_warnings,
            "max_clock_skew_seconds": self.max_clock_skew_seconds,
        }
