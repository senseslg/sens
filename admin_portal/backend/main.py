from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pymysql.err import IntegrityError

from .config import ADMIN_USERNAME, SESSION_SECRET, STATIC_DIR, TEMPLATES_DIR
from .db import (
    bootstrap_database,
    count_active_admin_users,
    create_admin_user,
    delete_admin_user,
    fetch_admin_user,
    fetch_admin_user_by_id,
    list_admin_users,
    mark_login,
    reset_admin_password,
    update_admin_user,
)
from .security import verify_password
from .system import collect_dashboard_snapshot


app = FastAPI(title="SENS 管理后台")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.middleware("http")
async def _disable_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.on_event("startup")
def _startup() -> None:
    bootstrap_database()


def _current_username(request: Request) -> str | None:
    return request.session.get("user")


def _current_user(request: Request) -> dict[str, Any] | None:
    username = _current_username(request)
    if not username:
        return None
    return fetch_admin_user(username)


def _require_user(request: Request) -> str:
    username = _current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return username


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": "SENS 管理后台"},
    )


@app.get("/api/me")
def me(request: Request):
    username = _current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="not_authenticated")
    user = fetch_admin_user(username)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="not_authenticated")
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "is_active": bool(user["is_active"]),
        "last_login_at": user["last_login_at"].isoformat() if user["last_login_at"] else None,
    }


@app.post("/api/login")
async def login(request: Request):
    payload = await request.json()
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        raise HTTPException(status_code=400, detail="missing_credentials")
    user = fetch_admin_user(username)
    if not user or not bool(user["is_active"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if not verify_password(password, user["password_salt"], user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    request.session["user"] = user["username"]
    mark_login(user["username"])
    return {
        "ok": True,
        "username": user["username"],
        "display_name": user["display_name"],
    }


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(request: Request, _: str = Depends(_require_user)):
    return collect_dashboard_snapshot()


@app.get("/api/health")
def health():
    snapshot = collect_dashboard_snapshot()
    return {
        "ok": True,
        "generated_at": snapshot["generated_at"],
        "local": snapshot["local"],
        "summary": snapshot["summary"],
    }


@app.get("/api/users")
def users(request: Request, _: str = Depends(_require_user)):
    return {"users": list_admin_users()}


@app.post("/api/users")
async def create_user(request: Request, _: str = Depends(_require_user)):
    payload = await request.json()
    username = str(payload.get("username", "")).strip()
    display_name = str(payload.get("display_name", "")).strip()
    password = str(payload.get("password", ""))
    is_active = bool(payload.get("is_active", True))
    if not username or not display_name or not password:
        raise HTTPException(status_code=400, detail="missing_user_fields")
    if len(username) > 64 or len(display_name) > 128:
        raise HTTPException(status_code=400, detail="user_fields_too_long")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="password_too_short")
    try:
        user = create_admin_user(username, display_name, password, is_active=is_active)
    except IntegrityError as exc:
        if exc.args and exc.args[0] == 1062:
            raise HTTPException(status_code=409, detail="username_exists") from exc
        raise
    return {"user": user}


@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request, _: str = Depends(_require_user)):
    payload = await request.json()
    display_name = str(payload.get("display_name", "")).strip()
    is_active = bool(payload.get("is_active", True))
    if not display_name:
        raise HTTPException(status_code=400, detail="missing_display_name")
    if len(display_name) > 128:
        raise HTTPException(status_code=400, detail="display_name_too_long")

    current = _current_user(request)
    if current and current["id"] == user_id and not is_active:
        raise HTTPException(status_code=400, detail="cannot_disable_self")

    user = update_admin_user(user_id, display_name, is_active)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    return {"user": user}


@app.post("/api/users/{user_id}/password")
async def reset_user_password(user_id: int, request: Request, _: str = Depends(_require_user)):
    payload = await request.json()
    password = str(payload.get("password", ""))
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="password_too_short")
    user = reset_admin_password(user_id, password)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    return {"user": user}


@app.delete("/api/users/{user_id}")
def remove_user(user_id: int, request: Request, _: str = Depends(_require_user)):
    current = _current_user(request)
    if current and current["id"] == user_id:
        raise HTTPException(status_code=400, detail="cannot_delete_self")

    target = fetch_admin_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="user_not_found")

    if target["is_active"] and count_active_admin_users() <= 1:
        raise HTTPException(status_code=400, detail="last_active_user")
    if not delete_admin_user(user_id):
        raise HTTPException(status_code=404, detail="user_not_found")
    return {"ok": True}


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
