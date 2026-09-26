#!/usr/bin/env bash
# External smoke tests against production's public endpoints. Used by the
# deploy job (after deploy.sh) and by the daily uptime cron.
#
#   smoke.sh [--site URL] [--disable-prod-delete]
#
# Checks:
#   1. frontend serves the marketing site (HTTP 200)
#   2. guest-sandbox mint returns 200 + a guest_ token
#   3. the minted token works for listing entries (sandbox org resolved)
#   4. (optional) sandbox workspace is cleared afterward
#
# Fails (non-zero) on any assertion miss.

set -euo pipefail

SITE="https://filebrsr.com"
DO_DELETE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --site) SITE="$2"; shift 2 ;;
    --disable-prod-delete) DO_DELETE=0; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

BASE="$SITE/backend/api/platform/csrd"
TOKEN=""

cleanup() {
  if [[ -n "$TOKEN" && "$DO_DELETE" == "1" ]]; then
    curl -fsS -o /dev/null -X DELETE "$BASE/guest/workspace" \
      -H "Authorization: Bearer $TOKEN" || true
    echo "   sandbox workspace cleared"
  fi
}
trap cleanup EXIT

echo "→ smoke: $SITE"

# 1. marketing page
code="$(curl -sS -o /dev/null -w '%{http_code}' -L "$SITE/products")"
[[ "$code" == "200" ]] || { echo "✖ /products -> HTTP $code (expected 200)" >&2; exit 1; }
echo "   ✓ /products 200"

# 2. guest mint
mint="$(curl -sS -w '\n%{http_code}' -X POST "$BASE/guest/session")"
body="${mint%$'\n'*}"; status="${mint##*$'\n'}"
[[ "$status" == "200" ]] || { echo "✖ guest/session -> HTTP $status" >&2; exit 1; }
TOKEN="$(printf '%s' "$body" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')"
[[ -n "$TOKEN" ]] || { echo "✖ mint returned no token: $body" >&2; exit 1; }
echo "   ✓ guest mint 200 (token ${TOKEN:0:13}…)"

# 3. authenticated guest call
code="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/entries?financial_year=FY2025" -H "Authorization: Bearer $TOKEN")" \
  || code="000"
[[ "$code" == "200" ]] || { echo "✖ entries (guest) -> HTTP $code (expected 200)" >&2; exit 1; }
echo "   ✓ guest entries 200"

echo "→ smoke OK"