"""One-password login. If DASHBOARD_PASSWORD is empty, the dashboard is open (local use)."""
import hashlib
import hmac
import time

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from .config import PASSWORD, secret_key

COOKIE = "navigara_session"
# Pages that must work without logging in.
OPEN_PREFIXES = ("/login", "/api/login", "/static/", "/favicon")


def _token() -> str:
    return hmac.new(secret_key(), PASSWORD.encode(), hashlib.sha256).hexdigest()


def password_ok(attempt: str) -> bool:
    ok = bool(PASSWORD) and hmac.compare_digest(attempt.encode(), PASSWORD.encode())
    if not ok:
        time.sleep(1)  # slows down guessing
    return ok


def is_logged_in(request: Request) -> bool:
    if not PASSWORD:
        return True
    cookie = request.cookies.get(COOKIE, "")
    return hmac.compare_digest(cookie, _token())


def set_login_cookie(response, request: Request) -> None:
    response.set_cookie(
        COOKIE, _token(), max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax",
        secure=request.url.scheme == "https",
    )


async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if is_logged_in(request) or path.startswith(OPEN_PREFIXES):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Please log in"}, status_code=401)
    return RedirectResponse("/login")
