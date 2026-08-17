"""c2pax — Python-native SDK для инспекции, верификации и работы с графом происхождения C2PA."""

from c2pax.api import diff, inspect, sign, verify
from c2pax.core.exceptions import (
    AssetError,
    AssetIOError,
    AssetNotFoundError,
    C2PAError,
    CertificateError,
    CorruptedManifestError,
    CyclicProvenanceError,
    IntegrityError,
    KeyPairMismatchError,
    ManifestError,
    ManifestNotFoundError,
    PolicyViolationError,
    SigningError,
    UnsupportedFormatError,
    UntrustedSignerError,
    VerificationError,
)
from c2pax.core.models import (
    AIProvenance,
    AssetInfo,
    AssetMetadata,
    IdentityInfo,
    ManifestStatus,
    PermissionsInfo,
)
from c2pax.core.provenance import (
    Action,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    Relationship,
)
from c2pax.core.source import AssetSource, AssetSourceAdapter
from c2pax.diff.semantic import SemanticDiff
from c2pax.signing.builder import Builder
from c2pax.signing.signer import Signer
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

__version__ = "0.1.0"

__all__ = [
    "AIProvenance",
    "Action",
    "AssetError",
    "AssetIOError",
    "AssetInfo",
    "AssetMetadata",
    "AssetNotFoundError",
    "AssetSource",
    "AssetSourceAdapter",
    "Builder",
    "C2PAError",
    "CertificateError",
    "CorruptedManifestError",
    "CyclicProvenanceError",
    "IdentityInfo",
    "IntegrityError",
    "IntegrityStatus",
    "KeyPairMismatchError",
    "ManifestError",
    "ManifestNotFoundError",
    "ManifestStatus",
    "PermissionsInfo",
    "PolicyViolationError",
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "Relationship",
    "SemanticDiff",
    "Signer",
    "SigningError",
    "TrustStatus",
    "TrustStore",
    "UnsupportedFormatError",
    "UntrustedSignerError",
    "ValidationError",
    "ValidationWarning",
    "VerificationError",
    "VerificationPolicy",
    "VerificationResult",
    "VerificationStatus",
    "diff",
    "inspect",
    "sign",
    "verify",
]
