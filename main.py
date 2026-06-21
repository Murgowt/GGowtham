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
from api.portfolio import router as portfolio_router
from db.database import init_db

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Brain", version="1.0.0")
STATIC_DIR = Path(__file__).parent / "static"

app.include_router(portfolio_router)


class LoginRequest(BaseModel):
    pin: str


@app.on_event("startup")
def on_startup() -> None:
    init_db()


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
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
