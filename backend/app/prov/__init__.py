"""
``app.prov`` — first-class provenance for FileBRSR (architectural principle #3).

Every disclosed number traces back to its signed source records through every
transformation, expressed as a W3C PROV-O graph that is canonicalised
(RFC 8785), SHA-256 hashed, and Ed25519-signed. The browser-side DSC
(eMudhra/Sify) dual signature is layered on top in Phase 5.

Public API::

    from app.prov import (
        CalculationProvenanceInput,
        build_signed_provenance,
        verify_signed_provenance,
    )

    signed = build_signed_provenance(CalculationProvenanceInput(...))
    assert verify_signed_provenance(signed)
"""

from __future__ import annotations

import base64

from app.prov.builder import (
    build_calculation_graph,
    build_signed_provenance,
    sign_graph,
)
from app.prov.canonicalize import canonical_hash, canonicalize, sha256_hex
from app.prov.models import (
    CalculationProvenanceInput,
    SignedProvenance,
)
from app.prov.signing import SigningError, get_signer, reset_signer, verify

__all__ = [
    "CalculationProvenanceInput",
    "SignedProvenance",
    "build_calculation_graph",
    "build_signed_provenance",
    "sign_graph",
    "canonicalize",
    "canonical_hash",
    "sha256_hex",
    "verify",
    "verify_signed_provenance",
    "get_signer",
    "reset_signer",
    "SigningError",
]


def verify_signed_provenance(signed: SignedProvenance) -> bool:
    """Re-canonicalise the stored graph and verify hash + Ed25519 signature.

    Returns True only if (a) the canonical SHA-256 of the graph matches the
    stored digest and (b) the Ed25519 signature over that canonical form is
    valid for the embedded public key. This is what an auditor re-runs to
    confirm a disclosed number has not been tampered with.
    """
    canonical, digest_hex = canonical_hash(signed.graph)
    if digest_hex != signed.canonical_sha256:
        return False
    try:
        signature = base64.b64decode(signed.signature_b64)
    except Exception:  # noqa: BLE001
        return False
    return verify(canonical, signature, signed.public_key_b64)
