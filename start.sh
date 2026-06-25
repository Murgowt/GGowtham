#!/usr/bin/env bash
set -euo pipefail

# Railway sets RAILWAY_SERVICE_NAME per service.
# brain-cron must run trigger_daily and exit; web runs uvicorn.
if [[ "${RAILWAY_SERVICE_NAME:-}" == *cron* ]]; then
  echo "Starting cron job for service: ${RAILWAY_SERVICE_NAME}"
  exec python -m jobs.trigger_daily
fi

echo "Starting web server for service: ${RAILWAY_SERVICE_NAME:-web}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
