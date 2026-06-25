"""Send daily portfolio summary (runs on the web server where subscriptions live).

Run manually: python -m jobs.daily_summary
"""

import logging
import sys

logging.basicConfig(level=logging.INFO)

from db.database import init_db
from integrations.daily_summary import send_daily_summary

logger = logging.getLogger("brain.daily_summary")


def main() -> int:
    init_db()
    try:
        result = send_daily_summary()
    except Exception:
        logger.exception("Daily summary failed")
        return 1

    if result.get("skipped"):
        return 0
    return 0 if result["sent"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
