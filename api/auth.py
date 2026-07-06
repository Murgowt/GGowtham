from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import settings

SESSION_COOKIE = "brain_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="brain-auth")


def verify_pin(pin: str) -> bool:
    return pin == settings.app_pin


def create_session_token() -> str:
    return _serializer().dumps({"authenticated": True})


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.production,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        secure=settings.production,
    )


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=SESSION_MAX_AGE)
        return bool(data.get("authenticated"))
    except (BadSignature, SignatureExpired):
        return False


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")


def require_income_pin(pin: str | None) -> None:
    """Extra PIN gate for income data (salary, allocations)."""
    if not pin:
        raise HTTPException(status_code=401, detail="PIN required for income")
    if not verify_pin(pin):
        raise HTTPException(status_code=403, detail="Invalid PIN")
