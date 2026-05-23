"""Unit tests for config and settings."""
import os
import pytest


class TestConfig:
    """Test configuration loading."""

    def test_settings_load(self):
        from app.config import get_settings
        settings = get_settings()
        assert settings.SUPABASE_URL is not None
        assert settings.MAX_FILE_SIZE_MB == 50

    def test_allowed_origins_split(self):
        from app.config import get_settings
        settings = get_settings()
        origins = settings.ALLOWED_ORIGINS.split(",")
        assert len(origins) >= 1
