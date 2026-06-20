"""
Deterministic canonicalisation + hashing for provenance graphs.

The charter calls for W3C PROV-O graphs canonicalised with **URDNA2015**
(RDF Dataset Normalisation) before hashing/signing. Full URDNA2015 requires
an RDF toolchain (``rdflib`` + ``pyld``) and is scheduled for the Phase-5
DSC integration. For Phase-1 we canonicalise the **JSON-LD serialisation**
with **RFC 8785 (JSON Canonicalization Scheme, JCS)**, which gives the same
guarantee we need *today*: byte-for-byte reproducible output for a given
logical graph, so the SHA-256 + Ed25519 signature is stable and verifiable.

To keep JCS number formatting from ever biasing an emission figure, the
provenance builder serialises all numeric values as **strings** in the
graph (see ``builder.py``). The canonical form therefore contains no JSON
floats, sidestepping the ECMAScript number-printing edge cases entirely —
which is also the correct posture for an audit artefact.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize(obj: Any) -> bytes:
    """Return the RFC 8785 (JCS) canonical UTF-8 encoding of ``obj``.

    Object keys are sorted lexicographically, insignificant whitespace is
    removed, and non-ASCII characters are preserved (UTF-8). The result is
    deterministic for a given logical structure regardless of input key
    order.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Hex-encoded SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(obj: Any) -> tuple[bytes, str]:
    """Canonicalise ``obj`` and return ``(canonical_bytes, sha256_hex)``."""
    canonical = canonicalize(obj)
    return canonical, sha256_hex(canonical)
