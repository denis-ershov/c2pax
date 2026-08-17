"""Схемы и валидаторы Pydantic v2 для c2pax."""

from __future__ import annotations

from datetime import datetime
from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field

    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False
    BaseModel = object  # type: ignore[assignment, misc]


if _PYDANTIC_AVAILABLE:

    class ActionSchema(BaseModel):
        name: str
        software: str | None = None
        timestamp: datetime | None = None
        parameters: dict[str, Any] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")

    class ProvenanceNodeSchema(BaseModel):
        id: str
        title: str
        format: str | None = None
        hash: str | None = None
        actions: list[ActionSchema] = Field(default_factory=list)
        metadata: dict[str, Any] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")

    class ProvenanceEdgeSchema(BaseModel):
        source_id: str
        target_id: str
        relationship: str
        model_config = ConfigDict(extra="ignore")

    class ProvenanceGraphSchema(BaseModel):
        root_id: str
        nodes: dict[str, ProvenanceNodeSchema] = Field(default_factory=dict)
        edges: list[ProvenanceEdgeSchema] = Field(default_factory=list)
        model_config = ConfigDict(extra="ignore")

    class AssetMetadataSchema(BaseModel):
        title: str | None = None
        format: str | None = None
        file_size_bytes: int | None = None
        created_at: datetime | None = None
        modified_at: datetime | None = None
        model_config = ConfigDict(extra="ignore")

    class IdentityInfoSchema(BaseModel):
        signer_name: str | None = None
        organization: str | None = None
        cert_issuer: str | None = None
        cert_serial: str | None = None
        country: str | None = None
        raw_x509_summary: dict[str, Any] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")

    class AIProvenanceSchema(BaseModel):
        generated: bool | None = None
        assisted: bool | None = None
        tools: list[str] = Field(default_factory=list)
        models: list[dict[str, Any]] = Field(default_factory=list)
        prompts: list[str] = Field(default_factory=list)
        raw_assertions: list[dict[str, Any]] = Field(default_factory=list)
        model_config = ConfigDict(extra="ignore")

    class PermissionsInfoSchema(BaseModel):
        data_mining_allowed: bool | None = None
        ai_training_allowed: bool | None = None
        raw_assertions: list[dict[str, Any]] = Field(default_factory=list)
        model_config = ConfigDict(extra="ignore")

    class ManifestStatusSchema(BaseModel):
        present: bool
        format_version: str | None = None
        claim_generator: str | None = None
        has_signature: bool = False
        label: str | None = None
        model_config = ConfigDict(extra="ignore")

    class AssetInfoSchema(BaseModel):
        has_c2pa: bool
        metadata: AssetMetadataSchema = Field(default_factory=AssetMetadataSchema)
        identity: IdentityInfoSchema = Field(default_factory=IdentityInfoSchema)
        provenance: ProvenanceGraphSchema | None = None
        ai: AIProvenanceSchema = Field(default_factory=AIProvenanceSchema)
        permissions: PermissionsInfoSchema = Field(default_factory=PermissionsInfoSchema)
        manifest_status: ManifestStatusSchema
        raw: dict[str, Any] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")

    class ValidationErrorSchema(BaseModel):
        code: str
        message: str
        details: dict[str, Any] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")

    class ValidationWarningSchema(BaseModel):
        code: str
        message: str
        details: dict[str, Any] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")

    class IntegrityStatusSchema(BaseModel):
        content_hash_matches: bool = True
        signature_valid: bool = True
        claims_intact: bool = True
        model_config = ConfigDict(extra="ignore")

    class TrustStatusSchema(BaseModel):
        signer_in_trust_store: bool = False
        tsa_trusted: bool | None = None
        cert_expired: bool = False
        model_config = ConfigDict(extra="ignore")

    class VerificationResultSchema(BaseModel):
        status: str
        valid: bool
        integrity: IntegrityStatusSchema
        trust: TrustStatusSchema
        errors: list[ValidationErrorSchema] = Field(default_factory=list)
        warnings: list[ValidationWarningSchema] = Field(default_factory=list)
        signer: IdentityInfoSchema | None = None
        timestamp: datetime | None = None
        policy_applied: dict[str, Any] = Field(default_factory=dict)
        raw_validation_status: list[dict[str, Any]] = Field(default_factory=list)
        model_config = ConfigDict(extra="ignore")

    class SemanticDiffSchema(BaseModel):
        added_actions: list[ActionSchema] = Field(default_factory=list)
        added_ingredients: list[ProvenanceNodeSchema] = Field(default_factory=list)
        signer_changed: bool = False
        previous_signer: IdentityInfoSchema | None = None
        current_signer: IdentityInfoSchema | None = None
        ai_provenance_changed: bool = False
        permissions_changed: bool = False
        metadata_diff: dict[str, list[Any]] = Field(default_factory=dict)
        model_config = ConfigDict(extra="ignore")


def to_pydantic(obj: Any) -> Any:
    """Конвертирует доменные dataclass-модели c2pax в схемы Pydantic v2."""
    if not _PYDANTIC_AVAILABLE:
        raise RuntimeError(
            "Пакет 'pydantic' не установлен. Установите 'pip install c2pax[pydantic]'."
        )

    from c2pax.core.models import AssetInfo
    from c2pax.diff.semantic import SemanticDiff
    from c2pax.verification.result import VerificationResult

    if isinstance(obj, AssetInfo):
        return AssetInfoSchema.model_validate(obj.to_dict())
    if isinstance(obj, VerificationResult):
        return VerificationResultSchema.model_validate(obj.to_dict())
    if isinstance(obj, SemanticDiff):
        return SemanticDiffSchema.model_validate(obj.to_dict())

    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    return obj
