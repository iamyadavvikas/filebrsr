from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    MAX_FILE_SIZE_MB: int = 50
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"
    RESEND_API_KEY: str = ""

    # Phase 3.2 — opt-in retrieval-based extraction layer. Off by default
    # so existing prod traffic is unaffected. Each filing with this on
    # costs ~8 Gemini Flash calls (free tier 1500 RPD = ~180 filings/day).
    ENABLE_RETRIEVAL_EXTRACTION: bool = False
    RETRIEVAL_MAX_DATAPOINTS: int = 40
    RETRIEVAL_BATCH_SIZE: int = 5
    RETRIEVAL_TOP_K: int = 3

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
