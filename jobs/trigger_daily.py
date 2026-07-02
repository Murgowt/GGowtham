"""Trigger push notification on the web app via HTTP (for Railway cron service).

Railway cron start command: python -m jobs.trigger_daily

Env vars:
  APP_BASE_URL  — e.g. https://your-app.up.railway.app
  CRON_SECRET   — must match web app
  CRON_MODE     — "daily" (portfolio summary), "spending" (budget alerts),
                  "budget_daily" (9 AM budget remaining), or "test" (ping). Default: daily

Production schedules:
  Portfolio (12:00 PM Central daily):
    CDT (Mar–Nov): 0 17 * * *
    CST (Nov–Mar): 0 18 * * *
  Spending alerts (hourly): 0 * * * *
  Budget remaining (9:00 AM Central daily):
    CDT (Mar–Nov): 0 14 * * *
    CST (Nov–Mar): 0 15 * * *
Testing schedule (every 5 minutes): */5 * * *
"""

import logging
import os
import sys

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain.trigger_daily")


def _normalize_base_url(raw: str) -> str:
    url = raw.strip().strip('"').strip("'")
    # Railway paste mistake: value set to "APP_BASE_URL=https://..."
    if url.upper().startswith("APP_BASE_URL="):
        url = url.split("=", 1)[1].strip()
    url = url.rstrip("/")
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _resolve_cron_mode() -> str:
    explicit = os.environ.get("CRON_MODE", "").strip().lower()
    if explicit:
        return explicit

    service = os.environ.get("RAILWAY_SERVICE_NAME", "").lower()
    if "spending" in service:
        return "spending"
    if "budget" in service:
        return "budget_daily"
    return "daily"


def run_trigger(*, dry_run: bool = False) -> int:
    base_url = _normalize_base_url(os.environ.get("APP_BASE_URL", ""))
    secret = os.environ.get("CRON_SECRET", "")
    mode = _resolve_cron_mode()

    if not base_url:
        logger.error(
            "APP_BASE_URL is required — value only, e.g. https://web-production-6a751.up.railway.app"
        )
        return 1
    if not secret and not dry_run:
        logger.error("CRON_SECRET is required")
        return 1

    path = (
        "cron/test" if mode == "test"
        else "cron/spending" if mode == "spending"
        else "cron/budget-daily" if mode == "budget_daily"
        else "cron/daily"
    )
    url = f"{base_url}/api/notifications/{path}"
    logger.info("Calling %s (CRON_MODE=%s)", url, mode)

    if dry_run:
        logger.info("Dry run — URL looks OK")
        return 0

    try:
        response = httpx.post(
            url,
            headers={"X-Cron-Secret": secret},
            timeout=15.0,
        )
    except httpx.HTTPError:
        logger.exception("Failed to reach Brain app at %s", url)
        return 1

    logger.info("Response %s: %s", response.status_code, response.text)
    if not response.is_success:
        return 1
    return 0


def main() -> int:
    dry_run = "--dry-run" in sys.argv or os.environ.get("DRY_RUN") == "1"
    return run_trigger(dry_run=dry_run)


if __name__ == "__main__":
    sys.exit(main())
