"""Trigger push notification on the web app via HTTP (for Railway cron service).

Railway cron start command: python -m jobs.trigger_daily

Env vars:
  APP_BASE_URL  — e.g. https://your-app.up.railway.app
  CRON_SECRET   — must match web app
  CRON_MODE     — "test" (simple ping) or "daily" (portfolio summary). Default: test

Production schedule (weekdays 4:30 PM ET): 30 21 * * 1-5
Testing schedule (every 5 minutes):       */5 * * * *
"""

import logging
import os
import sys

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain.trigger_daily")


def _normalize_base_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def main() -> int:
    base_url = _normalize_base_url(os.environ.get("APP_BASE_URL", ""))
    secret = os.environ.get("CRON_SECRET", "")
    mode = os.environ.get("CRON_MODE", "test").lower()

    if not base_url or base_url == "https://":
        logger.error("APP_BASE_URL is required (e.g. https://your-app.up.railway.app)")
        return 1
    if not secret:
        logger.error("CRON_SECRET is required")
        return 1

    path = "cron/test" if mode == "test" else "cron/daily"
    url = f"{base_url}/api/notifications/{path}"
    logger.info("Calling %s (CRON_MODE=%s)", url, mode)

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


if __name__ == "__main__":
    sys.exit(main())
