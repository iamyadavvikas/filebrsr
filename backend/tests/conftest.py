"""Shared test fixtures."""
import os
import pytest
from unittest.mock import patch, MagicMock

# Set test env vars before importing app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for all tests."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_table
    return mock_client


@pytest.fixture
def client(mock_supabase):
    """FastAPI test client with mocked dependencies."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    with patch("app.main.get_supabase_admin", return_value=mock_supabase):
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")
