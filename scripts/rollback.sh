#!/usr/bin/env bash
# Manual rollback. Run on the EC2 box.
# Usage:
#   ./rollback.sh              # rollback to the previous tag
#   ./rollback.sh <git-sha>    # rollback to a specific tag (must exist in ECR)
#
# Lists recent ECR tags if no arg and no .previous_tag found.

set -euo pipefail

cd "$(dirname "$0")/.."

# Source ECR_REGISTRY from .env
# shellcheck disable=SC1091
[[ -f .env ]] && set -a && source .env && set +a
: "${ECR_REGISTRY:?ECR_REGISTRY not set in .env}"
: "${AWS_REGION:=ap-south-1}"

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  TARGET="$(cat .previous_tag 2>/dev/null || echo "")"
  if [[ -z "$TARGET" ]]; then
    echo "Usage: ./rollback.sh <git-sha>"
    echo
    echo "Recent ECR tags for filebrsr-backend:"
    aws ecr describe-images --region "$AWS_REGION" \
      --repository-name filebrsr-backend \
      --query 'sort_by(imageDetails,& imagePushedAt)[-10:].[imageTags[0],imagePushedAt]' \
      --output table
    exit 1
  fi
fi

CURRENT="$(cat .current_tag 2>/dev/null || echo "")"
echo "→ Rolling back: $CURRENT → $TARGET"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

export TAG="$TARGET" ECR_REGISTRY
docker compose -f docker-compose.prod.yml pull frontend backend worker
docker compose -f docker-compose.prod.yml up -d --force-recreate frontend backend worker

# Persist
grep -v '^TAG=' .env > .env.tmp
echo "TAG=$TARGET" >> .env.tmp
mv .env.tmp .env

echo "$CURRENT" > .previous_tag
echo "$TARGET"  > .current_tag

echo "✓ Rolled back to $TARGET"
