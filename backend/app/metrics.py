"""Prometheus metrics for the FileBRSR backend.

Industry-neutral observability: RED metrics for every HTTP request plus a
handful of domain counters that track the provenance / ledger / extraction
pipeline. Everything lives in a single default registry so the ``/metrics``
endpoint can simply call :func:`prometheus_client.generate_latest`.

Business code should increment domain metrics via the small helper functions
at the bottom of this module rather than importing the metric objects
directly, so a missing/renamed metric never breaks a request path.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# ─── HTTP RED metrics ─────────────────────────────────────────────────────
# ``path`` is always a ROUTE TEMPLATE (e.g. "/api/verify/{calculation_id}")
# never a raw URL, to keep label cardinality bounded.
HTTP_REQUESTS = Counter(
    "filebrsr_http_requests_total",
    "Total HTTP requests processed.",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "filebrsr_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

# ─── Domain metrics ───────────────────────────────────────────────────────
PROV_SIGNATURES = Counter(
    "filebrsr_prov_signatures_total",
    "Provenance signing operations performed.",
)

PROV_VERIFICATIONS = Counter(
    "filebrsr_prov_verifications_total",
    "Public provenance verification attempts.",
    ["result"],  # pass | fail
)

LEDGER_APPENDS = Counter(
    "filebrsr_ledger_appends_total",
    "Merkle ledger append operations.",
    ["result"],  # ok | error
)

EXTRACTIONS = Counter(
    "filebrsr_extractions_total",
    "Document extraction pipeline runs.",
    ["result"],  # ok | error
)


# ─── Exposition ───────────────────────────────────────────────────────────
def render_latest() -> tuple[bytes, str]:
    """Return ``(payload, content_type)`` for the ``/metrics`` endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST


# ─── HTTP recording ───────────────────────────────────────────────────────
def observe_http(method: str, path: str, status: int, duration_seconds: float) -> None:
    """Record a single HTTP request's outcome and latency."""
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration_seconds)


# ─── Domain helpers (call from business code) ─────────────────────────────
def record_signature() -> None:
    PROV_SIGNATURES.inc()


def record_verification(passed: bool) -> None:
    PROV_VERIFICATIONS.labels(result="pass" if passed else "fail").inc()


def record_ledger_append(ok: bool = True) -> None:
    LEDGER_APPENDS.labels(result="ok" if ok else "error").inc()


def record_extraction(ok: bool = True) -> None:
    EXTRACTIONS.labels(result="ok" if ok else "error").inc()
