"""Тесты человекочитаемых объяснений VerificationResult.explain и SemanticDiff.explain."""

from datetime import datetime, timezone

from c2pax.core.models import IdentityInfo
from c2pax.core.provenance import Action
from c2pax.diff.semantic import SemanticDiff
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.result import (
    IntegrityStatus,
    TrustStatus,
    ValidationError,
    ValidationWarning,
    VerificationResult,
)
from c2pax.verification.status import VerificationStatus


def test_verification_result_explain_valid() -> None:
    res = VerificationResult(
        status=VerificationStatus.VALID,
        valid=True,
        integrity=IntegrityStatus(content_hash_matches=True, signature_valid=True),
        trust=TrustStatus(signer_in_trust_store=True),
        signer=IdentityInfo(
            signer_name="John Doe", organization="Media Inc", cert_issuer="C2PA Root CA"
        ),
        timestamp=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
        policy_applied=VerificationPolicy.standard(),
    )
    explanation = res.explain()
    assert "ДЕЙСТВИТЕЛЕН (VALID)" in explanation
    assert "John Doe" in explanation
    assert "Media Inc" in explanation
    assert "Совпадает" in explanation


def test_verification_result_explain_invalid_with_errors() -> None:
    res = VerificationResult(
        status=VerificationStatus.INVALID,
        valid=False,
        integrity=IntegrityStatus(content_hash_matches=False, signature_valid=False),
        trust=TrustStatus(signer_in_trust_store=False, cert_expired=True),
        errors=[ValidationError(code="hash.mismatch", message="Хэш контента не совпадает")],
        warnings=[ValidationWarning(code="tsa.missing", message="Штамп времени отсутствует")],
        policy_applied=VerificationPolicy.strict(),
    )
    explanation = res.explain()
    assert "НАРУШЕНА ЦЕЛОСТНОСТЬ (INVALID)" in explanation
    assert "Поврежден" in explanation
    assert "hash.mismatch" in explanation
    assert "tsa.missing" in explanation


def test_semantic_diff_explain() -> None:
    diff = SemanticDiff(
        signer_changed=True,
        previous_signer=IdentityInfo(signer_name="Alice"),
        current_signer=IdentityInfo(signer_name="Bob"),
        added_actions=[Action(name="c2pa.filtered", software="GIMP")],
        ai_provenance_changed=True,
        permissions_changed=True,
    )
    explanation = diff.explain()
    assert "Alice ➔ Bob" in explanation
    assert "c2pa.filtered" in explanation
    assert "ИИ-происхождение" in explanation
