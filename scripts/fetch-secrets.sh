#!/usr/bin/env bash
# Fetch secrets from AWS Secrets Manager and write .env for docker-compose.
# Idempotent — safe to run on every deploy or boot.
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"

SECRET_KEYS=(
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  NEXT_PUBLIC_SUPABASE_URL
  NEXT_PUBLIC_SUPABASE_ANON_KEY
  GEMINI_API_KEY
  GROQ_API_KEY
  ANTHROPIC_API_KEY
  SENTRY_DSN
  RESEND_API_KEY
  NEXT_PUBLIC_POSTHOG_KEY
)

for key in "${SECRET_KEYS[@]}"; do
  value=$(aws secretsmanager get-secret-value \
    --region "$AWS_REGION" \
    --secret-id "filebrsr/$key" \
    --query SecretString \
    --output text 2>/dev/null || echo "placeholder-replace-me")
  echo "${key}=${value}"
done
