import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_auth
from config import settings
from db.database import delete_push_subscription, list_push_subscriptions, save_push_subscription
from integrations.daily_summary import send_cron_test, send_daily_summary
from integrations.spending_alerts import check_and_send_spending_alerts, send_daily_budget_summary
from integrations.webpush import is_configured, send_to_subscription

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


def require_cron_secret(request: Request) -> None:
    if not settings.cron_secret:
        raise HTTPException(status_code=503, detail="Cron secret not configured")
    provided = request.headers.get("X-Cron-Secret")
    if not provided or provided != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


class SubscribeRequest(BaseModel):
    subscription: dict


@router.get("/config")
def notification_config(request: Request):
    require_auth(request)
    return {
        "enabled": settings.notifications_enabled and is_configured(),
        "vapid_public_key": settings.vapid_public_key if is_configured() else None,
    }


@router.get("/status")
def notification_status(request: Request):
    require_auth(request)
    subs = list_push_subscriptions()
    return {
        "configured": is_configured(),
        "subscribed": len(subs) > 0,
        "subscription_count": len(subs),
    }


@router.post("/subscribe")
def subscribe(request: Request, body: SubscribeRequest):
    require_auth(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    endpoint = body.subscription.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Invalid subscription")
    save_push_subscription(endpoint, body.subscription)
    return {"ok": True}


@router.delete("/subscribe")
def unsubscribe(request: Request):
    require_auth(request)
    subs = list_push_subscriptions()
    for sub in subs:
        delete_push_subscription(sub["endpoint"])
    return {"ok": True}


@router.post("/test")
def test_notification(request: Request):
    require_auth(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    subs = list_push_subscriptions()
    if not subs:
        raise HTTPException(status_code=400, detail="No push subscription. Enable notifications first.")

    sent = 0
    for sub in subs:
        if send_to_subscription(
            sub["subscription_json"],
            title="Brain",
            body="Portfolio notifications are working.",
        ):
            sent += 1

    if sent == 0:
        raise HTTPException(status_code=503, detail="Failed to send test notification")
    return {"ok": True, "sent": sent}


@router.post("/cron/test")
def cron_test_notification(request: Request):
    """Cron-only test push — same path as scheduled jobs, no portfolio fetch."""
    require_cron_secret(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    try:
        result = send_cron_test()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Cron test failed")
        raise HTTPException(status_code=503, detail=f"Cron test failed: {exc}") from exc
    if result.get("skipped"):
        raise HTTPException(status_code=400, detail="No push subscription on server")
    if result["sent"] == 0:
        raise HTTPException(status_code=503, detail="Failed to send cron test notification")
    return {"ok": True, **result}


@router.post("/cron/daily")
def cron_daily_summary(request: Request):
    """Called by Railway cron — must hit the web app (not a separate DB)."""
    require_cron_secret(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    try:
        result = send_daily_summary()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Daily summary failed")
        raise HTTPException(status_code=503, detail=f"Daily summary failed: {exc}") from exc
    if result.get("skipped"):
        return {"ok": True, **result, "message": "No subscribers — enable notifications in app"}
    if result["sent"] == 0:
        raise HTTPException(status_code=503, detail="Failed to send to any subscriber")
    return {"ok": True, **result}


@router.post("/cron/spending")
def cron_spending_alerts(request: Request):
    """Poll Plaid/Splitwise and push on new card charges or splits."""
    require_cron_secret(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    try:
        result = check_and_send_spending_alerts()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Spending alerts failed")
        raise HTTPException(status_code=503, detail=f"Spending alerts failed: {exc}") from exc
    if result.get("skipped"):
        return {"ok": True, **result, "message": "No subscribers — enable notifications in app"}
    return {"ok": True, **result}


@router.post("/cron/budget-daily")
def cron_daily_budget_summary(request: Request):
    """9 AM budget remaining — always notifies subscribers."""
    require_cron_secret(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    try:
        result = send_daily_budget_summary()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Daily budget summary failed")
        raise HTTPException(status_code=503, detail=f"Daily budget summary failed: {exc}") from exc
    if result.get("skipped"):
        return {"ok": True, **result, "message": "No subscribers — enable notifications in app"}
    if result["sent"] == 0:
        raise HTTPException(status_code=503, detail="Failed to send to any subscriber")
    return {"ok": True, **result}
