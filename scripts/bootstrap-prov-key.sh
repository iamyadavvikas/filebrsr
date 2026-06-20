#!/usr/bin/env bash
# One-time bootstrap for the provenance Ed25519 signing seed (KMS envelope).
#
# KMS cannot natively sign Ed25519, so we use a symmetric KMS key only to guard
# a 32-byte seed at rest. This script:
#   1. creates (idempotently) a symmetric KMS key + alias in ap-south-1
#   2. generates a fresh 32-byte Ed25519 seed
#   3. encrypts the seed with that KMS key
#   4. prints the base64 ciphertext for PROV_SIGNING_KEY_CIPHERTEXT_B64
#
# The plaintext seed is NEVER written to disk. The app decrypts it at boot
# (app/prov/signing.py:_build_signer) into an in-memory LocalEd25519Signer.
#
# Requires AWS CLI with kms:CreateKey/CreateAlias/Encrypt and python3.
# Idempotent for the key/alias; prints a NEW ciphertext each run (only keep one).

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
ALIAS="${PROV_KMS_ALIAS:-alias/filebrsr-prov-signing}"

echo "Region: $AWS_REGION   Alias: $ALIAS"

# --- 1. Create the symmetric KMS key + alias (idempotent) ---
KEY_ID="$(aws kms describe-key --key-id "$ALIAS" --region "$AWS_REGION" \
  --query 'KeyMetadata.KeyId' --output text 2>/dev/null || true)"

if [[ -z "$KEY_ID" || "$KEY_ID" == "None" ]]; then
  echo "→ Creating KMS key…"
  KEY_ID="$(aws kms create-key \
    --region "$AWS_REGION" \
    --description "FileBRSR provenance Ed25519 seed wrapping key" \
    --key-usage ENCRYPT_DECRYPT \
    --key-spec SYMMETRIC_DEFAULT \
    --tags TagKey=app,TagValue=filebrsr TagKey=purpose,TagValue=prov-signing \
    --query 'KeyMetadata.KeyId' --output text)"
  aws kms create-alias \
    --region "$AWS_REGION" \
    --alias-name "$ALIAS" \
    --target-key-id "$KEY_ID"
  echo "  created key: $KEY_ID"
else
  echo "→ Reusing existing KMS key: $KEY_ID"
fi

KEY_ARN="$(aws kms describe-key --key-id "$KEY_ID" --region "$AWS_REGION" \
  --query 'KeyMetadata.Arn' --output text)"

# --- 2. Generate a 32-byte Ed25519 seed (kept only in this process) ---
SEED_B64="$(python3 -c 'import os,base64;print(base64.b64encode(os.urandom(32)).decode())')"

# --- 3. Encrypt the seed with KMS ---
CIPHERTEXT_B64="$(aws kms encrypt \
  --region "$AWS_REGION" \
  --key-id "$KEY_ID" \
  --plaintext "fileb://<(printf '%s' "$SEED_B64" | base64 --decode)" \
  --query CiphertextBlob --output text 2>/dev/null || true)"

# `fileb://<(...)` process substitution is not portable; fall back to a temp
# file in memory-backed /dev/shm when available, else a secured temp file.
if [[ -z "$CIPHERTEXT_B64" || "$CIPHERTEXT_B64" == "None" ]]; then
  TMP_DIR="${XDG_RUNTIME_DIR:-/dev/shm}"
  [[ -d "$TMP_DIR" && -w "$TMP_DIR" ]] || TMP_DIR="$(mktemp -d)"
  SEED_BIN="$(mktemp "$TMP_DIR/prov-seed.XXXXXX")"
  trap 'rm -f "$SEED_BIN"' EXIT
  printf '%s' "$SEED_B64" | base64 --decode > "$SEED_BIN"
  CIPHERTEXT_B64="$(aws kms encrypt \
    --region "$AWS_REGION" \
    --key-id "$KEY_ID" \
    --plaintext "fileb://$SEED_BIN" \
    --query CiphertextBlob --output text)"
fi

unset SEED_B64

echo
echo "============================================================"
echo "Provenance signing key bootstrapped (KMS envelope)."
echo "Set these in the backend environment / GitHub secrets:"
echo "------------------------------------------------------------"
echo "PROV_SIGNING_KMS_KEY_ID          = $KEY_ARN"
echo "PROV_SIGNING_KEY_CIPHERTEXT_B64  = $CIPHERTEXT_B64"
echo "============================================================"
echo
echo "Grant the EC2 instance role kms:Decrypt on this key (see aws-setup.sh)."
echo "Verify after deploy: sign a calculation, restart the backend, re-verify —"
echo "the public key must be identical (same seed decrypted)."
