"""The web app: serves the pages and the data behind them."""
from contextlib import asynccontextmanager
import sqlite3
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import leads, practice
from .auth import COOKIE, auth_middleware, password_ok, set_login_cookie
from .config import BACKUP_DIR, DB_PATH, PASSWORD, PRACTICE, ROOT, TIMEZONE
from .db import connect, get_db, init_db

STATIC = ROOT / "static"
PAGES = ["leads", "dialer", "analytics", "scripts", "settings"]


@asynccontextmanager
async def lifespan(app):
    if PRACTICE:
        practice.reset_file()
    init_db()
    if PRACTICE:
        conn = connect()
        try:
            practice.seed(conn)
        finally:
            conn.close()
    yield


app = FastAPI(title="Navigara Dashboard", lifespan=lifespan, docs_url=None, redoc_url=None)
app.middleware("http")(auth_middleware)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.include_router(leads.router)


# ---------- pages ----------

@app.get("/")
def home():
    return RedirectResponse("/leads")


@app.get("/login")
def login_page():
    return FileResponse(STATIC / "pages" / "login.html")


def _page(name):
    def handler():
        return FileResponse(STATIC / "pages" / f"{name}.html")
    return handler


for _name in PAGES:
    app.get(f"/{_name}", name=f"page_{_name}")(_page(_name))


# ---------- login ----------

@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    if not password_ok(str(body.get("password", ""))):
        raise HTTPException(401, "Wrong password")
    response = JSONResponse({"ok": True})
    set_login_cookie(response, request)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login")
    response.delete_cookie(COOKIE)
    return response


# ---------- general ----------

@app.get("/api/me")
def me():
    return {"practice": PRACTICE, "login_required": bool(PASSWORD), "timezone": TIMEZONE}


@app.get("/api/overview")
def overview(conn=Depends(get_db)):
    def count(sql):
        return conn.execute(sql).fetchone()[0]
    return {
        "database_file": str(DB_PATH),
        "leads": count("SELECT COUNT(*) FROM leads"),
        "batches": count("SELECT COUNT(*) FROM batches WHERE deleted_at IS NULL"),
        "call_events": count("SELECT COUNT(*) FROM call_events"),
        "practice": PRACTICE,
    }


@app.get("/api/backup")
def backup():
    """Copy the whole database into data/backups/ and download it."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    prefix = "practice" if PRACTICE else "navigara"
    dest = BACKUP_DIR / f"{prefix}-backup-{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    src = connect()
    out = sqlite3.connect(dest)
    try:
        src.backup(out)  # safe even while the app is in use
    finally:
        out.close()
        src.close()
    return FileResponse(dest, filename=dest.name, media_type="application/octet-stream")
