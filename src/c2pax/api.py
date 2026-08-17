"""Публичный фасадный API c2pax (inspect, verify, diff, sign)."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from c2pax.backend import get_default_backend
from c2pax.backend.base import BaseC2paBackend
from c2pax.core.models import AssetInfo
from c2pax.core.parser import parse_raw_manifest_to_asset_info
from c2pax.core.source import AssetSource, AssetSourceAdapter
from c2pax.diff.semantic import SemanticDiff, compute_semantic_diff
from c2pax.signing.builder import sign as signing_sign
from c2pax.signing.signer import Signer
from c2pax.verification.cert_utils import (
    is_certificate_expired,
    parse_pem_certificates,
)
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.result import (
    IntegrityStatus,
    TrustStatus,
    ValidationError,
    ValidationWarning,
    VerificationResult,
)
from c2pax.verification.status import VerificationStatus
from c2pax.verification.trust import TrustStore


def inspect(
    source: AssetSource,
    filename: str | None = None,
    mime_type: str | None = None,
    backend: BaseC2paBackend | None = None,
) -> AssetInfo:
    """Извлекает задекларированную информацию манифеста C2PA (декларативный срез).

    Не осуществляет криптографическую валидацию подписи и соответствия доверенному хранилищу.
    """
    active_backend = backend or get_default_backend()
    with AssetSourceAdapter(source, filename=filename, mime_type=mime_type) as adapter:
        raw_manifest = active_backend.read_manifest_raw(adapter)
        return parse_raw_manifest_to_asset_info(raw_manifest, adapter)


def verify(
    source: AssetSource,
    policy: VerificationPolicy | None = None,
    trust_store: TrustStore | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    backend: BaseC2paBackend | None = None,
) -> VerificationResult:
    """Осуществляет полную криптографическую верификацию манифеста C2PA (доверенный срез).

    Проверяет цифровую подпись, целостность хэшей и соответствие политике VerificationPolicy.
    """
    active_backend = backend or get_default_backend()
    active_policy = policy or VerificationPolicy.standard()
    active_trust_store = trust_store or TrustStore()

    with AssetSourceAdapter(source, filename=filename, mime_type=mime_type) as adapter:
        raw_manifest, validation_statuses = active_backend.verify_raw(
            adapter,
            trust_store=active_trust_store,
        )

        # 1. Если манифест отсутствует
        if raw_manifest is None or not raw_manifest.get("manifests"):
            return VerificationResult(
                status=VerificationStatus.NO_MANIFEST,
                valid=False,
                integrity=IntegrityStatus(
                    content_hash_matches=False,
                    signature_valid=False,
                    claims_intact=False,
                ),
                trust=TrustStatus(signer_in_trust_store=False),
                errors=[
                    ValidationError(
                        code="manifest.not_found",
                        message="Манифест C2PA не найден в указанном ассете",
                    )
                ],
                policy_applied=active_policy,
                raw_validation_status=validation_statuses,
            )

        asset_info = parse_raw_manifest_to_asset_info(raw_manifest, adapter)
        active_id = raw_manifest.get("active_manifest")
        active_manifest = raw_manifest.get("manifests", {}).get(active_id, {})
        sig_info = active_manifest.get("signature_info", {})

        errors: list[ValidationError] = []
        warnings: list[ValidationWarning] = []

        # 2. Проверка целостности (Integrity)
        content_hash_matches = True
        signature_valid = True
        claims_intact = True

        for status_item in validation_statuses:
            code = status_item.get("code", "")
            explanation = status_item.get("explanation") or status_item.get("message", "")

            # Ошибки целостности
            if any(
                term in code.lower()
                for term in (
                    "hash.mismatch",
                    "claims_signature.invalid",
                    "signature.invalid",
                    "claimsignature.mismatch",
                    "corrupted",
                )
            ):
                content_hash_matches = False
                signature_valid = False
                errors.append(
                    ValidationError(
                        code=code,
                        message=explanation or "Нарушена криптографическая целостность ассета",
                        details=status_item,
                    )
                )
            elif "warning" in code.lower():
                warnings.append(
                    ValidationWarning(
                        code=code,
                        message=explanation or "Предупреждение валидации C2PA",
                        details=status_item,
                    )
                )

        # 3. Проверка подписанта и доверия (Trust)
        signer_in_trust_store = False
        cert_expired = False
        cert_pem = sig_info.get("cert")

        if cert_pem:
            try:
                certs = parse_pem_certificates(cert_pem)
                if certs:
                    target_cert = certs[0]
                    signer_in_trust_store = active_trust_store.is_signer_trusted(target_cert)
                    cert_expired = is_certificate_expired(target_cert)
            except Exception as e:
                errors.append(
                    ValidationError(
                        code="cert.parse_error",
                        message=f"Ошибка парсинга сертификата подписанта: {e}",
                    )
                )
        else:
            # Если нет PEM сертификата в явном виде
            if sig_info.get("issuer"):
                signer_in_trust_store = False

        # 4. Применение VerificationPolicy
        final_status = VerificationStatus.VALID

        # Криптографическая целостность
        if not content_hash_matches or not signature_valid or not claims_intact:
            final_status = VerificationStatus.INVALID

        # Проверка срока действия
        elif cert_expired and not active_policy.allow_expired_certs:
            final_status = VerificationStatus.INVALID
            errors.append(
                ValidationError(
                    code="cert.expired",
                    message="Срок действия сертификата подписанта истёк",
                )
            )

        # Проверка наличия в TrustStore
        elif active_policy.require_trusted_signer and not signer_in_trust_store:
            final_status = VerificationStatus.UNTRUSTED
            errors.append(
                ValidationError(
                    code="trust.untrusted_signer",
                    message="Сертификат подписанта не найден в списке доверенных (TrustStore)",
                )
            )

        # Проверка warnings при strict
        elif active_policy.fail_on_warnings and warnings:
            final_status = VerificationStatus.INVALID
            errors.append(
                ValidationError(
                    code="policy.fail_on_warnings",
                    message="Политика запрещает наличие предупреждений при валидации",
                )
            )

        # Если были критические ошибки
        if errors and final_status == VerificationStatus.VALID:
            final_status = VerificationStatus.INVALID

        integrity = IntegrityStatus(
            content_hash_matches=content_hash_matches,
            signature_valid=signature_valid,
            claims_intact=claims_intact,
        )
        trust = TrustStatus(
            signer_in_trust_store=signer_in_trust_store,
            cert_expired=cert_expired,
        )

        return VerificationResult(
            status=final_status,
            valid=(final_status == VerificationStatus.VALID),
            integrity=integrity,
            trust=trust,
            errors=errors,
            warnings=warnings,
            signer=asset_info.identity,
            timestamp=asset_info.provenance.actions[0].timestamp
            if (asset_info.provenance and asset_info.provenance.actions)
            else None,
            policy_applied=active_policy,
            raw_validation_status=validation_statuses,
        )


def diff(
    source1: AssetInfo | AssetSource,
    source2: AssetInfo | AssetSource,
    backend: BaseC2paBackend | None = None,
) -> SemanticDiff:
    """Выполняет семантическое сравнение двух версий цифрового ассета."""
    info1 = source1 if isinstance(source1, AssetInfo) else inspect(source1, backend=backend)
    info2 = source2 if isinstance(source2, AssetInfo) else inspect(source2, backend=backend)
    return compute_semantic_diff(info1, info2)


def sign(
    input_file: AssetSource,
    output_file: str | Path | BinaryIO,
    signer: Signer,
    title: str | None = None,
    creator: str | None = None,
    ai_tool: str | None = None,
    backend: BaseC2paBackend | None = None,
) -> bytes:
    """Быстрое наложение цифровой подписи C2PA на медиа-файл."""
    return signing_sign(
        input_file=input_file,
        output_file=output_file,
        signer=signer,
        title=title,
        creator=creator,
        ai_tool=ai_tool,
        backend=backend,
    )
