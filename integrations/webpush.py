import json
import logging

from pywebpush import WebPushException, webpush

from config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(
        settings.notifications_enabled
        and settings.vapid_public_key
        and settings.vapid_private_key
        and settings.vapid_subject
    )


def send_push(subscription_info: dict, payload: dict) -> None:
    if not is_configured():
        raise RuntimeError("Push notifications are not configured")

    webpush(
        subscription_info=subscription_info,
        data=json.dumps(payload),
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": settings.vapid_subject},
    )


def send_to_subscription(subscription_json: dict, title: str, body: str, url: str = "/") -> bool:
    try:
        send_push(subscription_json, {"title": title, "body": body, "url": url})
        return True
    except WebPushException as exc:
        logger.warning("Push failed: %s", exc)
        return False
