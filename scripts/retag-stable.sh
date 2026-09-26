#!/usr/bin/env bash
# Retags the just-smoked images as :stable. Only called after post-deploy
# smoke passes, so :stable always points at a verified-good build.
#
#   retag-stable.sh    (env: AWS_REGION, ECR_REGISTRY, BACKEND_REPO,
#                        FRONTEND_REPO, TAG)

set -euo pipefail

: "${AWS_REGION?}" : "${ECR_REGISTRY?}" : "${TAG?}"
: "${BACKEND_REPO:=filebrsr-backend}" "${FRONTEND_REPO:=filebrsr-frontend}"

retag() {
  local repo="$1" tag="$2" manifest
  manifest="$(aws ecr batch-get-image --region "$AWS_REGION" \
    --repository-name "$repo" \
    --image-ids "imageTag=$TAG" \
    --query 'images[0].imageManifest' --output text)"
  [[ -n "$manifest" && "$manifest" != "None" ]] \
    || { echo "✖ could not read manifest for $repo:$TAG" >&2; return 1; }
  aws ecr put-image --region "$AWS_REGION" \
    --repository-name "$repo" --image-tag "$tag" \
    --image-manifest "$manifest" >/dev/null
  echo "→ $repo:$tag = $TAG"
}

retag "$FRONTEND_REPO" "stable"
retag "$BACKEND_REPO" "stable"
echo "✓ :stable retagged to $TAG"