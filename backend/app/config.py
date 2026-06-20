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

    # ─── Data residency (principle #6: AWS Mumbai only) ──────────────────
    # All data-bearing infra must live in ap-south-1. Surfaced here so the
    # app can assert/log its region and refuse to start misconfigured in prod.
    DATA_REGION: str = "ap-south-1"

    # ─── Provenance signing (principle #3) ───────────────────────────────
    # Prod: KMS envelope — PROV_SIGNING_KMS_KEY_ID encrypts a 32-byte Ed25519
    # seed, stored base64 in PROV_SIGNING_KEY_CIPHERTEXT_B64; decrypted at boot
    # via kms.Decrypt → in-process LocalEd25519Signer (KMS can't sign Ed25519).
    # Dev/CI: plaintext base64 seed in PROV_SIGNING_KEY_B64.
    # Neither set → ephemeral key (non-reproducible; refused in production).
    PROV_SIGNING_KMS_KEY_ID: str = ""
    PROV_SIGNING_KEY_CIPHERTEXT_B64: str = ""
    PROV_SIGNING_KEY_B64: str = ""
    PROV_SIGNING_KEY_ID: str = "local-dev"

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
