#!/usr/bin/env bash
# Runs deploy/rollback on the EC2 box via SSM Run Command (no SSH key).
#
#   ssm-run.sh deploy              # sync+deploy the config staged in S3
#   ssm-run.sh rollback [target]   # roll the box back (optionally to a tag)
#
# Env: AWS_REGION, EC2_HOST (public EIP), S3_CONFIG_BUCKET, TAG,
#      ECR_REGISTRY (used by deploy.sh on the box)

set -euo pipefail

: "${AWS_REGION:?AWS_REGION required}"
: "${EC2_HOST:?EC2_HOST required}"
: "${S3_CONFIG_BUCKET:?S3_CONFIG_BUCKET required}"
MODE="${1:?mode required: deploy|rollback}"
TARGET="${2:-}"

INSTANCE_ID="$(
  aws ec2 describe-addresses --region "$AWS_REGION" \
    --public-ips "$EC2_HOST" \
    --query 'Addresses[0].InstanceId' --output text
)"
[[ -n "$INSTANCE_ID" && "$INSTANCE_ID" != "None" ]] \
  || { echo "✖ no EC2 instance mapped to $EC2_HOST" >&2; exit 1; }
echo "→ EC2 instance: $INSTANCE_ID"

case "$MODE" in
  deploy)
    ;;
  rollback)
    ;;
  *)
    echo "✖ mode must be deploy|rollback" >&2
    exit 2
    ;;
esac

PARAMS="$(mktemp /tmp/ssm-params.XXXXXX.json)"
trap 'rm -f "$PARAMS"' EXIT

SSM_COMMANDS="$(cat <<EOF
export AWS_DEFAULT_REGION=$AWS_REGION AWS_REGION=$AWS_REGION
export ECR_REGISTRY=${ECR_REGISTRY:-} TAG=${TAG:-}
set -euo pipefail
cd ~/filebrsr
EOF
)"

if [[ "$MODE" == "deploy" ]]; then
  SSM_COMMANDS+="

aws s3 cp s3://${S3_CONFIG_BUCKET}/filebrsr/config.tgz /tmp/filebrsr-config.tgz --no-progress >/dev/null
tar -xzf /tmp/filebrsr-config.tgz -C ~/filebrsr/
chmod +x scripts/deploy.sh scripts/rollback.sh
./scripts/deploy.sh
"
else
  SSM_COMMANDS+="
$([[ -n "$TARGET" ]] && printf 'bash ./scripts/rollback.sh %q\n' "$TARGET" || echo './scripts/rollback.sh')
"
fi

export SSM_COMMANDS PARAMS
python3 - <<'PY'
import json, os
params = json.dumps({"commands": [os.environ["SSM_COMMANDS"]]})
open(os.environ["PARAMS"], "w").write(params)
PY

CMD_ID="$(
  aws ssm send-command --region "$AWS_REGION" \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "file://$PARAMS" \
    --comment "filebrsr $MODE (${TAG:-no-tag})" \
    --query 'Command.CommandId' --output text
)"
echo "→ SSM command $MODE: $CMD_ID"

# Poll until terminal status, then print output.
STATUS=Pending
for _ in $(seq 1 180); do
  STATUS="$(aws ssm get-command-invocation --region "$AWS_REGION" \
    --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
    --query 'Status' --output text 2>/dev/null || echo Pending)"
  case "$STATUS" in
    Success | Failed | Cancelled | TimedOut) break ;;
  esac
  sleep 5
done

aws ssm get-command-invocation --region "$AWS_REGION" \
  --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
  --query '[StatusDetails, StandardOutputContent, StandardErrorContent]' \
  --output text 2>/dev/null || true

[[ "$STATUS" == "Success" ]] || { echo "✖ SSM $MODE failed (status=$STATUS)" >&2; exit 1; }
echo "→ SSM $MODE complete"