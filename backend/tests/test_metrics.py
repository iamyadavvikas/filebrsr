"""
Observability — Prometheus ``/metrics`` endpoint and domain counters.

Acceptance:
- ``GET /metrics`` returns 200 in Prometheus exposition format and exposes the
  RED metrics + domain counter names.
- Recording a signature / verification / ledger append / extraction bumps the
  corresponding counter sample.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from prometheus_client import CONTENT_TYPE_LATEST

from app import metrics
from app.main import app


def _sample_value(counter, **labels) -> float:
    """Read the current value of a (possibly labelled) counter sample."""
    if labels:
        return counter.labels(**labels)._value.get()
    return counter._value.get()


@pytest.mark.asyncio
async def test_metrics_endpoint_exposition_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(CONTENT_TYPE_LATEST.split(";")[0])
    body = resp.text
    assert "filebrsr_http_requests_total" in body
    assert "filebrsr_http_request_duration_seconds" in body
    assert "filebrsr_prov_signatures_total" in body
    assert "filebrsr_prov_verifications_total" in body
    assert "filebrsr_ledger_appends_total" in body
    assert "filebrsr_extractions_total" in body


def test_record_signature_increments():
    before = _sample_value(metrics.PROV_SIGNATURES)
    metrics.record_signature()
    assert _sample_value(metrics.PROV_SIGNATURES) == before + 1


def test_record_verification_pass_and_fail():
    before_pass = _sample_value(metrics.PROV_VERIFICATIONS, result="pass")
    before_fail = _sample_value(metrics.PROV_VERIFICATIONS, result="fail")
    metrics.record_verification(True)
    metrics.record_verification(False)
    assert _sample_value(metrics.PROV_VERIFICATIONS, result="pass") == before_pass + 1
    assert _sample_value(metrics.PROV_VERIFICATIONS, result="fail") == before_fail + 1


def test_record_ledger_append():
    before = _sample_value(metrics.LEDGER_APPENDS, result="ok")
    metrics.record_ledger_append(ok=True)
    assert _sample_value(metrics.LEDGER_APPENDS, result="ok") == before + 1


def test_record_extraction():
    before = _sample_value(metrics.EXTRACTIONS, result="error")
    metrics.record_extraction(ok=False)
    assert _sample_value(metrics.EXTRACTIONS, result="error") == before + 1


@pytest.mark.asyncio
async def test_http_request_recorded():
    before = _sample_value(
        metrics.HTTP_REQUESTS, method="GET", path="/health", status="200"
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/health")
    after = _sample_value(
        metrics.HTTP_REQUESTS, method="GET", path="/health", status="200"
    )
    assert after == before + 1
