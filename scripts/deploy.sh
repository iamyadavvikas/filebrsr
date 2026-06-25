#!/usr/bin/env bash
# Runs on the EC2 box. Called by CI after images are pushed to ECR.
# Usage: TAG=<git-sha> ECR_REGISTRY=<acct>.dkr.ecr.<region>.amazonaws.com ./deploy.sh
#
# Assumes:
#   - cwd = ~/filebrsr (where docker-compose.prod.yml lives)
#   - ~/filebrsr/.env contains runtime secrets
#   - awscli + docker installed; EC2 instance role has ECR pull permission
#   - .current_tag records the live tag (used for rollback)

set -euo pipefail

: "${TAG:?TAG env var required (git short sha)}"
: "${ECR_REGISTRY:?ECR_REGISTRY env var required}"
: "${AWS_REGION:=ap-south-1}"

cd "$(dirname "$0")/.."

PREV_TAG="$(cat .current_tag 2>/dev/null || echo "")"
echo "→ Deploying TAG=$TAG  (previous=$PREV_TAG)"

# 1. Authenticate Docker to ECR
echo "→ ECR login"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# 2. Pull the new images (will fail loudly if missing — good)
echo "→ Pulling images"
export TAG ECR_REGISTRY
docker compose -f docker-compose.prod.yml pull frontend backend worker

# 3. Fetch secrets from AWS Secrets Manager onto .env
echo "→ Fetching secrets"
AWS_REGION="${AWS_REGION:-ap-south-1}"
"$(dirname "$0")/fetch-secrets.sh" > .env.tmp 2>/dev/null
grep -v '^TAG=' .env 2>/dev/null >> .env.tmp || true
grep -v '^ECR_REGISTRY=' .env.tmp > .env.tmp2 || true
mv .env.tmp2 .env.tmp
echo "TAG=$TAG"                   >> .env.tmp
echo "ECR_REGISTRY=$ECR_REGISTRY" >> .env.tmp
echo "AWS_REGION=$AWS_REGION"     >> .env.tmp
mv .env.tmp .env

# 4. Recreate containers (zero-downtime for nginx: it only restarts if config changed)
echo "→ Bringing up services"
docker compose -f docker-compose.prod.yml up -d --remove-orphans \
  --force-recreate frontend backend worker

# Observability stack (Prometheus scrapes backend; Grafana serves /grafana/)
docker compose -f docker-compose.prod.yml up -d prometheus grafana

# nginx + certbot only restart if their config / image changed
docker compose -f docker-compose.prod.yml up -d nginx certbot

# compose won't recreate nginx when only the mounted nginx.conf changed on disk,
# so explicitly reload to pick up config changes (e.g. the /grafana/ route).
# Zero-downtime; skipped if the new config fails validation.
if docker exec filebrsr-nginx-1 nginx -t >/dev/null 2>&1; then
  docker exec filebrsr-nginx-1 nginx -s reload || true
  echo "→ nginx config reloaded"
else
  echo "⚠ nginx -t failed; keeping previous config"
fi

# 5. Health check — give containers 60s to become healthy
echo "→ Health check (up to 60s)"
ok=0
for _ in $(seq 1 12); do
  sleep 5
  fe="$(docker inspect --format='{{.State.Health.Status}}' filebrsr-frontend-1 2>/dev/null || echo unknown)"
  be="$(docker inspect --format='{{.State.Health.Status}}' filebrsr-backend-1  2>/dev/null || echo unknown)"
  echo "   frontend=$fe  backend=$be"
  if [[ "$fe" == "healthy" && "$be" == "healthy" ]]; then
    ok=1
    break
  fi
done

if [[ "$ok" != "1" ]]; then
  echo "✖ Health check failed. Rolling back to $PREV_TAG"
  if [[ -n "$PREV_TAG" ]]; then
    TAG="$PREV_TAG" docker compose -f docker-compose.prod.yml up -d \
      --force-recreate frontend backend worker
    echo "↩ Rolled back to $PREV_TAG"
  else
    echo "⚠ No previous tag recorded; manual intervention required"
  fi
  exit 1
fi

# 6. Record the new live tag and prune old images
echo "$TAG" > .current_tag
docker image prune -af --filter "until=168h" >/dev/null 2>&1 || true

echo "✓ Deploy complete. Live tag: $TAG"
