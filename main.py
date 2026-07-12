import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.auth import (
    clear_session_cookie,
    create_session_token,
    is_authenticated,
    set_session_cookie,
    verify_pin,
)
from api.budget import router as budget_router
from api.goals import router as goals_router
from api.investments import router as investments_router
from api.notifications import router as notifications_router
from api.portfolio import router as portfolio_router
from api.spending import router as spending_router
from config import settings
from db.database import init_db

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Brain", version="1.0.0")
STATIC_DIR = Path(__file__).parent / "static"

app.include_router(portfolio_router)
app.include_router(investments_router)
app.include_router(notifications_router)
app.include_router(spending_router)
app.include_router(budget_router)
app.include_router(goals_router)


class LoginRequest(BaseModel):
    pin: str


def _database_kind(url: str) -> str:
    if url.startswith("postgresql"):
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "other"


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger = logging.getLogger("brain")
    db_kind = _database_kind(settings.database_url)
    if settings.production and db_kind == "sqlite" and "/data/" not in settings.database_url:
        logger.warning(
            "DATABASE_URL uses ephemeral SQLite (%s). "
            "Add a Railway volume at /data or attach PostgreSQL so Plaid and "
            "notification subscriptions survive redeploys.",
            settings.database_url,
        )
    logger.info(
        "Brain started (production=%s, db=%s, mock=%s, snaptrade=%s, plaid=%s)",
        settings.production,
        db_kind,
        settings.mock_integrations,
        bool(settings.snaptrade_client_id and settings.snaptrade_consumer_key),
        bool(settings.plaid_client_id and settings.plaid_secret),
    )


@app.post("/api/login")
def login(body: LoginRequest, response: Response):
    if not verify_pin(body.pin):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    token = create_session_token()
    set_session_cookie(response, token)
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    return {"authenticated": is_authenticated(request)}


@app.get("/")
def index():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
