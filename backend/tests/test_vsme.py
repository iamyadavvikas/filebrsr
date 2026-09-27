"""VSME feeder tests: catalog integrity + ESRS upgrade prefill."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def client():
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_vsme_catalog_covers_b1_to_b11(client):
    resp = await client.get("/api/platform/csrd/vsme-basic")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] >= 25
    areas = {m["area"] for m in body["metrics"]}
    for area in ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]:
        assert area in areas, f"missing VSME area {area}"


def test_vsme_maps_to_all_resolve_to_real_esrs_ids():
    from app.esrs_datapoints import by_id
    from app.vsme import VSME_BASIC

    bad = []
    for m in VSME_BASIC:
        for dp_id in m["maps_to"]:
            if by_id(dp_id) is None:
                bad.append((m["code"], dp_id))
    assert bad == [], f"feeder maps to unknown ESRS ids: {bad}"


@pytest.mark.asyncio
async def test_vsme_upgrade_prefills_and_dedupes(client):
    resp = await client.post(
        "/api/platform/csrd/vsme-upgrade",
        json={
            "answers": {
                "VB3.3": 1200.5,          # Scope 1 -> E1.E1-6.44
                "VB3.4": 800,             # Scope 2 -> E1.E1-6.44 (dedupe keeps first)
                "VB1.1": "Boundary note",  # narrative -> BP-1.3
                "VB2.1": "Policy text",    # no numeric target -> unmapped
                "VBXX.9": "junk",          # unknown code -> unmapped
                "VB6.1": None,             # empty -> skipped
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_dp = {e["datapoint_id"]: e for e in body["entries"]}
    assert by_dp["E1.E1-6.44"]["value"] == 1200.5
    assert by_dp["E1.E1-6.44"]["source"] == "vsme-feeder"
    assert by_dp["ESRS2.BP-1.3"]["value"] == "Boundary note"
    assert "VB2.1" in body["unmapped"]
    assert "VBXX.9" in body["unmapped"]
    assert body["count"] == len(body["entries"])
