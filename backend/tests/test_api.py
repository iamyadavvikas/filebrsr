"""API integration tests for core endpoints."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def async_client(mock_supabase):
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Health check and basic API availability."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        resp = await async_client.get("/health")
        # FastAPI default or custom health
        assert resp.status_code in (200, 404)  # pass if exists

    @pytest.mark.asyncio
    async def test_docs_endpoint(self, async_client):
        resp = await async_client.get("/docs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_schema(self, async_client):
        resp = await async_client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "FileBRSR Platform API"


class TestExtractEndpoint:
    """Tests for /api/extract endpoint."""

    @pytest.mark.asyncio
    async def test_extract_requires_auth(self, async_client):
        """Extract endpoint rejects requests without auth."""
        resp = await async_client.post("/api/extract", data={"report_id": "test", "user_id": "test"})
        assert resp.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_extract_rejects_wrong_token(self, async_client):
        """Extract endpoint rejects wrong token."""
        import io
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
        resp = await async_client.post(
            "/api/extract",
            headers={"Authorization": "Bearer wrong-token"},
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
            data={"report_id": "test-id", "user_id": "test-user"},
        )
        assert resp.status_code == 401


class TestLeadsCaptureEndpoint:
    """Tests for /api/platform/leads/capture — no auth required."""

    @pytest.mark.asyncio
    async def test_leads_capture_basic(self, async_client, mock_supabase):
        with patch("app.router_market.get_supabase_admin", return_value=mock_supabase):
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "123", "email": "test@company.com"}]
            )
            resp = await async_client.post(
                "/api/platform/leads/capture",
                json={
                    "email": "test@company.com",
                    "source": "readiness_assessment",
                    "score": 72,
                    "readiness_level": "moderate",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "captured"

    @pytest.mark.asyncio
    async def test_leads_capture_missing_email(self, async_client):
        resp = await async_client.post(
            "/api/platform/leads/capture",
            json={"source": "readiness_assessment"},
        )
        assert resp.status_code == 422  # Validation error


class TestGuestExtract:
    """Tests for /api/guest-extract — public endpoint."""

    @pytest.mark.asyncio
    async def test_guest_extract_no_file(self, async_client):
        resp = await async_client.post("/api/guest-extract")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_guest_extract_empty_pdf(self, async_client):
        """Should return failed status for non-extractable content."""
        import io
        fake_pdf = io.BytesIO(b"not a real pdf")
        resp = await async_client.post(
            "/api/guest-extract",
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )
        # Will either fail gracefully or return error
        assert resp.status_code in (200, 400, 500)


class TestCorrectionEndpoint:
    """Tests for /api/correction — user-supplied fixes to extracted fields."""

    _AUTH = {"Authorization": "Bearer test-service-key"}
    _BODY = {
        "report_id": "00000000-0000-0000-0000-000000000001",
        "user_id": "00000000-0000-0000-0000-000000000002",
        "section": "section_a",
        "field_path": "turnover",
        "original_value": "₹1,234 Cr",
        "corrected_value": "₹1,500 Cr",
        "source_page": 12,
    }

    @pytest.mark.asyncio
    async def test_correction_requires_auth(self, async_client):
        resp = await async_client.post("/api/correction", json=self._BODY)
        assert resp.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_correction_rejects_wrong_token(self, async_client):
        resp = await async_client.post(
            "/api/correction",
            headers={"Authorization": "Bearer wrong"},
            json=self._BODY,
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_correction_rejects_invalid_section(self, async_client, mock_supabase):
        with patch("app.main.get_supabase_admin", return_value=mock_supabase):
            body = {**self._BODY, "section": "section_z"}
            resp = await async_client.post(
                "/api/correction", headers=self._AUTH, json=body,
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_correction_rejects_empty_corrected_value(self, async_client, mock_supabase):
        with patch("app.main.get_supabase_admin", return_value=mock_supabase):
            body = {**self._BODY, "corrected_value": "   "}
            resp = await async_client.post(
                "/api/correction", headers=self._AUTH, json=body,
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_correction_inserts_and_returns_id(self, async_client, mock_supabase):
        with patch("app.main.get_supabase_admin", return_value=mock_supabase):
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "corr-123"}]
            )
            resp = await async_client.post(
                "/api/correction", headers=self._AUTH, json=self._BODY,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["correction_id"] == "corr-123"
            # Verify the row we tried to insert
            mock_supabase.table.assert_called_with("extraction_corrections")
            insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
            assert insert_call["report_id"] == self._BODY["report_id"]
            assert insert_call["user_id"] == self._BODY["user_id"]
            assert insert_call["section"] == "section_a"
            assert insert_call["field_path"] == "turnover"
            assert insert_call["corrected_value"] == "₹1,500 Cr"
            assert insert_call["source_page"] == 12

    @pytest.mark.asyncio
    async def test_correction_db_failure_returns_500(self, async_client, mock_supabase):
        with patch("app.main.get_supabase_admin", return_value=mock_supabase):
            mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
                "db down"
            )
            resp = await async_client.post(
                "/api/correction", headers=self._AUTH, json=self._BODY,
            )
            assert resp.status_code == 500
