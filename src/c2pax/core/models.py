"""Доменная модель c2pax (AssetInfo, AssetMetadata, IdentityInfo, AIProvenance, PermissionsInfo)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from c2pax.core.provenance import ProvenanceGraph


@dataclass(slots=True)
class AssetMetadata:
    """Технические метаданные медиа-ассета."""

    title: str | None = None
    format: str | None = None
    file_size_bytes: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "format": self.format,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
        }


@dataclass(slots=True)
class IdentityInfo:
    """Задекларированная информация о создателе и подписанте (не проверенная криптографически)."""

    signer_name: str | None = None
    organization: str | None = None
    cert_issuer: str | None = None
    cert_serial: str | None = None
    country: str | None = None
    raw_x509_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signer_name": self.signer_name,
            "organization": self.organization,
            "cert_issuer": self.cert_issuer,
            "cert_serial": self.cert_serial,
            "country": self.country,
            "raw_x509_summary": self.raw_x509_summary,
        }


@dataclass(slots=True)
class AIProvenance:
    """Фактологические утверждения о генеративном или вспомогательном ИИ-происхождении."""

    generated: bool | None = None  # True = полностью сгенерировано, None = нет утверждения
    assisted: bool | None = None  # True = использовался при редактировании
    tools: list[str] = field(default_factory=list)
    models: list[dict[str, Any]] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    raw_assertions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated": self.generated,
            "assisted": self.assisted,
            "tools": self.tools,
            "models": self.models,
            "prompts": self.prompts,
            "raw_assertions": self.raw_assertions,
        }


@dataclass(slots=True)
class PermissionsInfo:
    """Декларации ограничений использования и data-mining (c2pa.data_mining)."""

    data_mining_allowed: bool | None = None
    ai_training_allowed: bool | None = None
    raw_assertions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_mining_allowed": self.data_mining_allowed,
            "ai_training_allowed": self.ai_training_allowed,
            "raw_assertions": self.raw_assertions,
        }


@dataclass(slots=True)
class ManifestStatus:
    """Служебный статус наличия контейнера C2PA без валидации доверия."""

    present: bool
    format_version: str | None = None
    claim_generator: str | None = None
    has_signature: bool = False
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "format_version": self.format_version,
            "claim_generator": self.claim_generator,
            "has_signature": self.has_signature,
            "label": self.label,
        }


@dataclass(slots=True)
class AssetInfo:
    """Полный декларативный срез информации об ассете (результат inspect())."""

    has_c2pa: bool
    metadata: AssetMetadata = field(default_factory=AssetMetadata)
    identity: IdentityInfo = field(default_factory=IdentityInfo)
    provenance: ProvenanceGraph | None = None
    ai: AIProvenance = field(default_factory=AIProvenance)
    permissions: PermissionsInfo = field(default_factory=PermissionsInfo)
    manifest_status: ManifestStatus = field(default_factory=lambda: ManifestStatus(present=False))
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_c2pa": self.has_c2pa,
            "metadata": self.metadata.to_dict(),
            "identity": self.identity.to_dict(),
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "ai": self.ai.to_dict(),
            "permissions": self.permissions.to_dict(),
            "manifest_status": self.manifest_status.to_dict(),
            "raw": self.raw,
        }
