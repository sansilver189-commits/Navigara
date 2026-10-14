"""Dialer: today's list, today's numbers, results, and starting calls through Twilio.

Safety: the browser only ever sends a lead id. The server looks up the number, picks which of
your numbers to call from, and signs a short-lived "ticket". The Twilio Function that places
the call refuses any ticket without a valid signature, so nobody can make it dial anything else.
"""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, time as dtime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from . import config
from .areacodes import distance, location
from .db import get_db, get_setting, set_setting
from .results import ANSWERED, DIALER_RESULTS, RESULTS, RETRY_ONCE
from .util import area_code, local_tz, pretty_phone, utc_now

router = APIRouter()

PRACTICE_NUMBERS = ["+14155550100", "+16505550100", "+14045550100"]


def numbers() -> list[str]:
    if config.PRACTICE:
        return PRACTICE_NUMBERS
    return config.TWILIO_NUMBERS


def today_start_utc() -> str:
    """Midnight today in your time zone, as a UTC timestamp."""
    tz = local_tz()
    midnight = datetime.combine(datetime.now(tz).date(), dtime.min, tzinfo=tz)
    return midnight.astimezone(timezone.utc).isoformat(timespec="seconds")


def _today_stats(conn, start):
    rows = conn.execute(
        "SELECT result FROM call_events WHERE source = 'dialer' AND ignored = 0 AND created_at >= ?",
        (start,),
    ).fetchall()
    dials = len(rows)
    answered = sum(r["result"] in ANSWERED for r in rows)
    booked = sum(r["result"] == "booked" for r in rows)
    return {
        "dials": dials, "answered": answered, "booked": booked,
        "answer_rate": round(100 * answered / dials) if dials else None,
        "booking_rate": round(100 * booked / dials) if dials else None,
    }


def _list(conn, start):
    rows = conn.execute(f"""
        WITH ev AS (SELECT * FROM call_events WHERE ignored = 0)
        SELECT l.id, l.name, l.contact_name, l.title, l.phone, l.score, l.grade, l.pitch,
               (SELECT COUNT(*) FROM ev WHERE ev.lead_id = l.id) AS n_events,
               (SELECT COUNT(*) FROM ev WHERE ev.lead_id = l.id
                    AND ev.result NOT IN ({",".join("?" * len(RETRY_ONCE))})) AS n_final,
               (SELECT MIN(created_at) FROM ev WHERE ev.lead_id = l.id AND ev.source = 'dialer'
                    AND ev.created_at >= ?) AS first_today,
               (SELECT MAX(created_at) FROM ev WHERE ev.lead_id = l.id) AS last_call,
               (SELECT result FROM ev WHERE ev.lead_id = l.id ORDER BY created_at DESC, id DESC LIMIT 1) AS last_result
        FROM leads l LEFT JOIN batches b ON b.id = l.batch_id
        WHERE b.deleted_at IS NULL AND l.status = 'ready' AND l.phone IS NOT NULL
    """, (*RETRY_ONCE, start)).fetchall()

    callback_before = (datetime.fromisoformat(start) - timedelta(days=config.CALL_LATER_DAYS - 1)).isoformat()
    new, retry, done = [], [], []
    for r in rows:
        item = {"id": r["id"], "company": r["name"], "contact": r["contact_name"], "title": r["title"],
                "phone_pretty": pretty_phone(r["phone"]), "score": r["score"], "grade": r["grade"],
                "pitch": r["pitch"], "today_result": None, "event_id": None}
        if r["first_today"]:
            last = conn.execute(
                "SELECT id, result FROM call_events WHERE lead_id = ? AND ignored = 0 AND source = 'dialer' "
                "AND created_at >= ? "
                "ORDER BY created_at DESC, id DESC LIMIT 1", (r["id"], start)).fetchone()
            item.update(kind="today", today_result=last["result"], event_id=last["id"],
                        sort=r["first_today"])
            done.append(item)
        elif r["n_events"] == 0:
            new.append({**item, "kind": "new"})
        elif r["n_events"] == 1 and r["n_final"] == 0:
            retry.append({**item, "kind": "retry"})  # one miss before today: one more try
        elif r["last_result"] == "call_later" and r["last_call"] < callback_before:
            retry.append({**item, "kind": "callback"})  # they asked to be called later
    new.sort(key=lambda x: -(x["score"] or 0))
    retry.sort(key=lambda x: -(x["score"] or 0))
    done.sort(key=lambda x: x["sort"])
    return retry + new + done


@router.get("/api/dialer/state")
def state(conn=Depends(get_db)):
    start = today_start_utc()
    return {
        "calling": "practice" if config.PRACTICE else ("twilio" if config.TWILIO_ENABLED else "off"),
        "numbers": [pretty_phone(n) for n in numbers()],
        "goal": int(get_setting(conn, "daily_goal", 60)),
        "stats": _today_stats(conn, start),
        "results": {k: RESULTS[k] for k in DIALER_RESULTS},
        "leads": _list(conn, start),
    }


@router.post("/api/dialer/goal")
def set_goal(body: dict, conn=Depends(get_db)):
    goal = int(body.get("goal") or 0)
    if not 1 <= goal <= 2000:
        raise HTTPException(400, "Goal must be between 1 and 2000")
    set_setting(conn, "daily_goal", goal)
    return {"goal": goal}


@router.post("/api/dialer/result")
def save_result(body: dict, conn=Depends(get_db)):
    """Each result is a new row. Changing today's pick marks the old row ignored (never deleted)."""
    lead_id, result = int(body.get("lead_id") or 0), body.get("result")
    if result not in DIALER_RESULTS:
        raise HTTPException(400, "Unknown result")
    if not conn.execute("SELECT 1 FROM leads WHERE id = ?", (lead_id,)).fetchone():
        raise HTTPException(404, "Lead not found")
    replace = body.get("replace_event_id")
    if replace:
        conn.execute("UPDATE call_events SET ignored = 1, ignored_at = ? WHERE id = ? AND lead_id = ?",
                     (utc_now(), int(replace), lead_id))
    from_number = body.get("from_number")
    event_id = conn.execute(
        "INSERT INTO call_events(lead_id, result, source, from_number, call_sid, duration_sec, script_id, created_at) "
        "VALUES(?, ?, 'dialer', ?, ?, ?, ?, ?)",
        (lead_id, result, from_number if from_number in numbers() else None, body.get("call_sid"),
         body.get("duration_sec"), body.get("script_id"), utc_now()),
    ).lastrowid
    conn.commit()
    return {"event_id": event_id, "stats": _today_stats(conn, today_start_utc())}


def pick_number(conn, lead_phone: str) -> str | None:
    """Same area code first, else the nearest. Ties take turns (least recently used goes next)."""
    nums = numbers()
    if not nums:
        return None
    ac = area_code(lead_phone)
    same = [n for n in nums if area_code(n) == ac]
    if same:
        candidates = same
    else:
        here = location(ac)
        # Rounded to 100 km so numbers in the same region count as equally near.
        dist = {n: round(distance(here, location(area_code(n))) / 100) if here else 0 for n in nums}
        best = min(dist.values())
        candidates = [n for n in nums if dist[n] == best]
    if len(candidates) == 1:
        return candidates[0]
    last_used = {r["from_number"]: r["t"] for r in conn.execute(
        "SELECT from_number, MAX(created_at) t FROM call_events WHERE from_number IS NOT NULL GROUP BY from_number")}
    return min(candidates, key=lambda n: last_used.get(n, ""))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@router.post("/api/dialer/ticket")
def ticket(body: dict, conn=Depends(get_db)):
    """The browser asks to call a lead by id. Only the server knows which number that is."""
    lead = conn.execute("SELECT id, phone FROM leads WHERE id = ?", (int(body.get("lead_id") or 0),)).fetchone()
    if not lead or not lead["phone"]:
        raise HTTPException(404, "Lead has no phone number")
    from_number = pick_number(conn, lead["phone"])
    if config.PRACTICE:
        return {"ticket": "practice", "from": from_number, "from_pretty": pretty_phone(from_number)}
    if not config.TWILIO_ENABLED:
        raise HTTPException(400, "Calling is not set up")
    payload = _b64(json.dumps({"lead": lead["id"], "to": lead["phone"], "from": from_number,
                               "exp": int(time.time()) + 120}).encode())
    sig = _b64(hmac.new(config.DIAL_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
    return {"ticket": f"{payload}.{sig}", "from": from_number, "from_pretty": pretty_phone(from_number)}


@router.get("/api/dialer/token")
def token():
    """Short-lived (1 hour) permission for this browser to place calls through Twilio."""
    if not config.TWILIO_ENABLED:
        raise HTTPException(400, "Calling is not set up")
    from twilio.jwt.access_token import AccessToken
    from twilio.jwt.access_token.grants import VoiceGrant
    t = AccessToken(config.TWILIO_ACCOUNT_SID, config.TWILIO_API_KEY, config.TWILIO_API_SECRET,
                    identity="navigara-dialer", ttl=3600)
    t.add_grant(VoiceGrant(outgoing_application_sid=config.TWILIO_TWIML_APP_SID))
    return {"token": t.to_jwt()}
