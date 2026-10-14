"""All settings come from the .env file (see .env.example). Nothing secret lives in the code."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR = DATA_DIR / "backups"

# Practice mode: same dashboard, made-up leads, a throwaway database, pretend calls.
PRACTICE = os.environ.get("NAVIGARA_PRACTICE") == "1"
DB_PATH = DATA_DIR / ("practice.db" if PRACTICE else "navigara.db")

PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
TIMEZONE = os.environ.get("TIMEZONE", "America/New_York").strip() or "America/New_York"

HOST = "127.0.0.1"  # only reachable from this computer
PORT = int(os.environ.get("PORT", "8000")) + (1 if PRACTICE else 0)


def secret_key() -> bytes:
    """Random key used to sign the login cookie. Created once, kept in data/ (never in git)."""
    path = DATA_DIR / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_hex(32))
    return path.read_text().strip().encode()
