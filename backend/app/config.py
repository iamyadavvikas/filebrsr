from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    MAX_FILE_SIZE_MB: int = 50

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
