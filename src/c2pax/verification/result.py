"""Результат верификации и человекочитаемое объяснение (VerificationResult, explain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from c2pax.core.models import IdentityInfo
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.status import VerificationStatus


@dataclass(slots=True)
class ValidationError:
    """Ошибка валидации цифрового манифеста."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


@dataclass(slots=True)
class ValidationWarning:
    """Предупреждение при валидации манифеста."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


@dataclass(slots=True)
class IntegrityStatus:
    """Статус криптографической целостности контента и подписи."""

    content_hash_matches: bool = True
    signature_valid: bool = True
    claims_intact: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_hash_matches": self.content_hash_matches,
            "signature_valid": self.signature_valid,
            "claims_intact": self.claims_intact,
        }


@dataclass(slots=True)
class TrustStatus:
    """Статус доверия к сертификатам подписанта и службы меток времени."""

    signer_in_trust_store: bool = False
    tsa_trusted: bool | None = None
    cert_expired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "signer_in_trust_store": self.signer_in_trust_store,
            "tsa_trusted": self.tsa_trusted,
            "cert_expired": self.cert_expired,
        }


@dataclass(slots=True)
class VerificationResult:
    """Полный результат проверки C2PA манифеста с учетом политики верификации."""

    status: VerificationStatus
    valid: bool
    integrity: IntegrityStatus = field(default_factory=IntegrityStatus)
    trust: TrustStatus = field(default_factory=TrustStatus)
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)
    signer: IdentityInfo | None = None
    timestamp: datetime | None = None
    policy_applied: VerificationPolicy = field(default_factory=VerificationPolicy.permissive)
    raw_validation_status: list[dict[str, Any]] = field(default_factory=list)

    def explain(self) -> str:
        """Формирует структурированное человекочитаемое объяснение вердикта валидации на русском языке."""
        lines: list[str] = []

        status_titles: dict[VerificationStatus, str] = {
            VerificationStatus.VALID: "✅ ДЕЙСТВИТЕЛЕН (VALID)",
            VerificationStatus.INVALID: "❌ НАРУШЕНА ЦЕЛОСТНОСТЬ (INVALID)",
            VerificationStatus.UNTRUSTED: "⚠️ НЕ ДОВЕРЕН (UNTRUSTED)",
            VerificationStatus.NO_MANIFEST: "ℹ️ МАНИФЕСТ C2PA ОТСУТСТВУЕТ (NO_MANIFEST)",
            VerificationStatus.UNSUPPORTED: "🚫 НЕПОДДЕРЖИВАЕМЫЙ ФОРМАТ (UNSUPPORTED)",
            VerificationStatus.ERROR: "🛑 ОШИБКА ВЕРИФИКАЦИИ (ERROR)",
        }

        lines.append(f"Вердикт: {status_titles.get(self.status, str(self.status))}")
        lines.append("-" * 50)

        # 1. Информация о подписанте
        if self.signer:
            lines.append("Информация о подписанте:")
            lines.append(f"  • Имя / Сертификат: {self.signer.signer_name or 'Не указано'}")
            if self.signer.organization:
                lines.append(f"  • Организация:      {self.signer.organization}")
            if self.signer.cert_issuer:
                lines.append(f"  • Издатель (CA):    {self.signer.cert_issuer}")
            if self.signer.cert_serial:
                lines.append(f"  • Серийный номер:   {self.signer.cert_serial}")
        else:
            lines.append("Подписант: Не определен")

        # 2. Метка времени
        if self.timestamp:
            lines.append(f"Дата подписи: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        lines.append("")

        # 3. Проверка целостности
        lines.append("Проверка целостности (Integrity):")
        lines.append(
            f"  • Хэш контента:    {'Совпадает' if self.integrity.content_hash_matches else '❌ Поврежден / Не совпадает'}"
        )
        lines.append(
            f"  • Цифровая подпись: {'Действительна' if self.integrity.signature_valid else '❌ Недействительна'}"
        )

        # 4. Проверка доверия
        lines.append("Проверка доверия (Trust):")
        lines.append(
            f"  • Наличие в TrustStore: {'Да (Доверен)' if self.trust.signer_in_trust_store else 'Нет (Не доверен)'}"
        )
        if self.trust.cert_expired:
            lines.append("  • Срок действия сертификата: ❌ Истёк")
        else:
            lines.append("  • Срок действия сертификата: Действителен")

        if self.trust.tsa_trusted is not None:
            lines.append(
                f"  • Доверенная метка TSA: {'Да' if self.trust.tsa_trusted else 'Нет / Не подтверждена'}"
            )

        # 5. Ошибки и предупреждения
        if self.errors:
            lines.append("")
            lines.append("Ошибки:")
            for err in self.errors:
                lines.append(f"  ❌ [{err.code}] {err.message}")

        if self.warnings:
            lines.append("")
            lines.append("Предупреждения:")
            for warn in self.warnings:
                lines.append(f"  ⚠️ [{warn.code}] {warn.message}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "valid": self.valid,
            "integrity": self.integrity.to_dict(),
            "trust": self.trust.to_dict(),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "signer": self.signer.to_dict() if self.signer else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "policy_applied": self.policy_applied.to_dict(),
            "raw_validation_status": self.raw_validation_status,
        }
