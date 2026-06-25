from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_auth
from config import settings
from db.database import delete_push_subscription, list_push_subscriptions, save_push_subscription
from integrations.daily_summary import send_daily_summary
from integrations.webpush import is_configured, send_to_subscription

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


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
        raise HTTPException(status_code=503, detail="Failed to send daily summary") from exc
    return {"ok": True, **result}
