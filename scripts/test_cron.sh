#!/usr/bin/env bash
# Test cron trigger locally before deploying to Railway.
#
# Usage:
#   ./scripts/test_cron.sh dry-run
#   ./scripts/test_cron.sh live
#
# For live, set in .env or export:
#   APP_BASE_URL=https://web-production-6a751.up.railway.app
#   CRON_SECRET=your-secret
#   CRON_MODE=test   (or daily)

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODE="${1:-dry-run}"

case "$MODE" in
  dry-run)
    echo "=== Dry run (URL only) ==="
    APP_BASE_URL="${APP_BASE_URL:-https://web-production-6a751.up.railway.app}" \
      python -m jobs.trigger_daily --dry-run
    ;;
  live)
    echo "=== Live call to production ==="
    if [[ -z "${CRON_SECRET:-}" ]]; then
      echo "Error: CRON_SECRET not set (add to .env or export it)"
      exit 1
    fi
    python -m jobs.trigger_daily
    ;;
  curl)
    echo "=== curl (no Python) ==="
    if [[ -z "${CRON_SECRET:-}" ]]; then
      echo "Error: CRON_SECRET not set"
      exit 1
    fi
    BASE="${APP_BASE_URL:-https://web-production-6a751.up.railway.app}"
    BASE="${BASE#APP_BASE_URL=}"
    [[ "$BASE" != https://* ]] && BASE="https://${BASE#https://}"
    BASE="${BASE%/}"
    ENDPOINT="${CRON_MODE:-test}"
    [[ "$ENDPOINT" == "daily" ]] && PATH_SUFFIX="cron/daily" || PATH_SUFFIX="cron/test"
    curl -sS -X POST "${BASE}/api/notifications/${PATH_SUFFIX}" \
      -H "X-Cron-Secret: ${CRON_SECRET}" \
      -w "\nHTTP %{http_code}\n"
    ;;
  *)
    echo "Usage: $0 {dry-run|live|curl}"
    exit 1
    ;;
esac
