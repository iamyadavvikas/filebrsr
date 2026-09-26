#!/usr/bin/env bash
# Packages runtime config and uploads it to S3, staged for the deploy box.
# The box pulls + extracts this tarball in the same SSM command that deploys.
#
#   sync-config.sh    (env: AWS_REGION, S3_CONFIG_BUCKET)

set -euo pipefail

: "${S3_CONFIG_BUCKET:?S3_CONFIG_BUCKET required}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARBALL="$(mktemp /tmp/filebrsr-config.XXXXXX.tgz)"

trap 'rm -f "$TARBALL"' EXIT

tar -czf "$TARBALL" -C "$REPO_ROOT" \
  docker-compose.prod.yml \
  nginx/nginx.conf \
  scripts/deploy.sh \
  scripts/rollback.sh \
  scripts/smoke.sh \
  observability/prometheus/prometheus.prod.yml \
  observability/grafana/provisioning \
  observability/grafana/dashboards

aws s3 cp "$TARBALL" "s3://${S3_CONFIG_BUCKET}/filebrsr/config.tgz" \
  --region "$AWS_REGION" --no-progress >/dev/null

echo "→ config.tgz uploaded to s3://${S3_CONFIG_BUCKET}/filebrsr/"
ls -la "$TARBALL"