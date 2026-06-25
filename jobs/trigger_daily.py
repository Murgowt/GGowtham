"""Trigger daily summary on the web app via HTTP (for Railway cron service).

The cron service has a separate SQLite file and cannot see push subscriptions.
This script calls the main Brain app, which owns the subscription database.

Railway cron start command: python -m jobs.trigger_daily

Production schedule (weekdays 4:30 PM ET): 30 21 * * 1-5
Testing schedule (every 5 minutes):       */5 * * * *

Requires env vars: APP_BASE_URL, CRON_SECRET
"""

import logging
import os
import sys

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain.trigger_daily")


def main() -> int:
    base_url = os.environ.get("APP_BASE_URL", "").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")

    if not base_url or not secret:
        logger.error("APP_BASE_URL and CRON_SECRET are required")
        return 1

    url = f"{base_url}/api/notifications/cron/daily"
    try:
        response = httpx.post(
            url,
            headers={"X-Cron-Secret": secret},
            timeout=120.0,
        )
    except httpx.HTTPError:
        logger.exception("Failed to reach Brain app at %s", url)
        return 1

    logger.info("Response %s: %s", response.status_code, response.text)
    return 0 if response.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
