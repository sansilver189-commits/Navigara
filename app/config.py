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

# A lead marked "Call Later" comes back on the Dialer this many days later.
CALL_LATER_DAYS = max(1, int(os.environ.get("CALL_LATER_DAYS", "3")))

# Only call between these hours in the LEAD's own time zone (24-hour clock). 8 to 20 = 8am-8pm.
CALL_HOURS = tuple(int(x) for x in os.environ.get("CALL_HOURS", "8-20").split("-"))

# ---- Twilio (calling). All must be set, or the Dialer works as a plain list. ----
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_API_KEY = os.environ.get("TWILIO_API_KEY", "").strip()
TWILIO_API_SECRET = os.environ.get("TWILIO_API_SECRET", "").strip()
TWILIO_TWIML_APP_SID = os.environ.get("TWILIO_TWIML_APP_SID", "").strip()
# Shared with the small Twilio Function that places calls; proves a call request came from you.
DIAL_SECRET = os.environ.get("DIAL_SECRET", "").strip()
TWILIO_NUMBERS = [n.strip() for n in os.environ.get("TWILIO_NUMBERS", "").split(",") if n.strip()]
TWILIO_ENABLED = all([TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, TWILIO_TWIML_APP_SID,
                      DIAL_SECRET, TWILIO_NUMBERS])
