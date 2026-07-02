import os
from unittest.mock import patch

from jobs import trigger_daily


def test_resolve_cron_mode_from_service_name():
    with patch.dict(os.environ, {"RAILWAY_SERVICE_NAME": "Spending-cron"}, clear=False):
        os.environ.pop("CRON_MODE", None)
        assert trigger_daily._resolve_cron_mode() == "spending"


def test_resolve_cron_mode_explicit_overrides_name():
    with patch.dict(os.environ, {"CRON_MODE": "budget_daily", "RAILWAY_SERVICE_NAME": "Spending-cron"}, clear=False):
        assert trigger_daily._resolve_cron_mode() == "budget_daily"
