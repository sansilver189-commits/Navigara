"""Small helpers: phone numbers and time."""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import TIMEZONE


def normalize_phone(raw) -> str | None:
    """Turn '(512) 555-0123' into '+15125550123'. Returns None if it is not a usable number."""
    if not raw:
        return None
    raw = str(raw).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return "+" + digits
    return None


def area_code(phone: str | None) -> str | None:
    if phone and phone.startswith("+1") and len(phone) == 12:
        return phone[2:5]
    return None


def pretty_phone(phone: str | None) -> str:
    if phone and phone.startswith("+1") and len(phone) == 12:
        return f"({phone[2:5]}) {phone[5:8]}-{phone[8:]}"
    return phone or ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_tz() -> ZoneInfo:
    try:
        return ZoneInfo(TIMEZONE)
    except Exception:
        return ZoneInfo("America/New_York")
