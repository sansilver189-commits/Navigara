"""Analytics: is the calling working?

Only calls made from the Dialer count (source = 'dialer'). Results logged by hand on the
Leads page are bookkeeping, except Showed / Signed, which can only be logged there.
"""
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from .db import get_db
from .results import ANSWERED
from .util import local_tz, pretty_phone

router = APIRouter()

THIN = 20  # fewer calls than this and a rate is marked "too thin to trust"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _rate(part, whole):
    return round(100 * part / whole) if whole else None


def _utc(d: date, tz) -> str:
    return datetime.combine(d, dtime.min, tzinfo=tz).astimezone(timezone.utc).isoformat(timespec="seconds")


@router.get("/api/analytics")
def analytics(start: str = "", end: str = "", conn=Depends(get_db)):
    tz = local_tz()
    today = datetime.now(tz).date()
    try:
        d_end = date.fromisoformat(end) if end else today
        d_start = date.fromisoformat(start) if start else d_end - timedelta(days=29)
    except ValueError:
        raise HTTPException(400, "Dates must look like 2026-10-14")
    if d_start > d_end:
        d_start, d_end = d_end, d_start

    events = conn.execute(
        """SELECT e.*, l.industry, l.pitch FROM call_events e JOIN leads l ON l.id = e.lead_id
           WHERE e.source = 'dialer' AND e.ignored = 0 AND e.created_at >= ? AND e.created_at < ?
           ORDER BY e.created_at""",
        (_utc(d_start, tz), _utc(d_end + timedelta(days=1), tz)),
    ).fetchall()

    # ---- funnel ----
    dials = len(events)
    answered = sum(e["result"] in ANSWERED for e in events)
    booked_leads = {e["lead_id"] for e in events if e["result"] == "booked"}
    later = defaultdict(set)
    if booked_leads:
        marks = ",".join("?" * len(booked_leads))
        for r in conn.execute(f"SELECT lead_id, result FROM call_events WHERE ignored = 0 "
                              f"AND result IN ('showed', 'signed') AND lead_id IN ({marks})", list(booked_leads)):
            later[r["result"]].add(r["lead_id"])
    steps = [("Dials", dials), ("Answered", answered), ("Booked", len(booked_leads)),
             ("Showed", len(later["showed"])), ("Signed", len(later["signed"]))]
    funnel = [{"label": label, "n": n, "rate": _rate(n, steps[i - 1][1]) if i else None,
               "thin": i > 0 and steps[i - 1][1] < THIN} for i, (label, n) in enumerate(steps)]

    # ---- by hour and weekday (your time zone) ----
    hours = [{"label": h, "dials": 0, "answered": 0} for h in range(24)]
    days = [{"label": d, "dials": 0, "answered": 0} for d in DAYS]
    for e in events:
        t = datetime.fromisoformat(e["created_at"]).astimezone(tz)
        for bucket in (hours[t.hour], days[t.weekday()]):
            bucket["dials"] += 1
            bucket["answered"] += e["result"] in ANSWERED
    for b in hours + days:
        b["rate"] = _rate(b["answered"], b["dials"])
        b["thin"] = b["dials"] < THIN

    # ---- by industry: per business called, not per dial ----
    per_lead = {}
    for e in events:
        p = per_lead.setdefault(e["lead_id"], {"industry": e["industry"] or "Unknown", "reached": False, "booked": False})
        p["reached"] |= e["result"] in ANSWERED
        p["booked"] |= e["result"] == "booked"
    groups = defaultdict(lambda: {"called": 0, "reached": 0, "booked": 0})
    for p in per_lead.values():
        g = groups[p["industry"]]
        g["called"] += 1
        g["reached"] += p["reached"]
        g["booked"] += p["booked"]
    by_industry = sorted(
        ({"label": k, **v, "reach_rate": _rate(v["reached"], v["called"]),
          "book_rate": _rate(v["booked"], v["called"]), "thin": v["called"] < THIN} for k, v in groups.items()),
        key=lambda x: -x["called"])

    # ---- by phone number (plus last 7 days, to spot a number that stopped working) ----
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    recent = defaultdict(lambda: [0, 0])
    for r in conn.execute("SELECT from_number, result FROM call_events WHERE source = 'dialer' AND ignored = 0 "
                          "AND from_number IS NOT NULL AND created_at >= ?", (week_ago,)):
        recent[r["from_number"]][0] += 1
        recent[r["from_number"]][1] += r["result"] in ANSWERED
    nums = defaultdict(lambda: {"dials": 0, "answered": 0, "booked": 0})
    for e in events:
        if e["from_number"]:
            n = nums[e["from_number"]]
            n["dials"] += 1
            n["answered"] += e["result"] in ANSWERED
            n["booked"] += e["result"] == "booked"
    by_number = [{"label": pretty_phone(k), **v, "rate": _rate(v["answered"], v["dials"]),
                  "week_dials": recent[k][0], "week_rate": _rate(recent[k][1], recent[k][0]),
                  "thin": v["dials"] < THIN, "week_thin": recent[k][0] < THIN}
                 for k, v in sorted(nums.items(), key=lambda kv: -kv[1]["dials"])]

    # ---- by script (shown once two scripts have calls) ----
    names = {}
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'scripts'").fetchone():
        names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM scripts")}
    sc = defaultdict(lambda: {"dials": 0, "answered": 0, "booked": 0})
    for e in events:
        if e["script_id"]:
            s = sc[e["script_id"]]
            s["dials"] += 1
            s["answered"] += e["result"] in ANSWERED
            s["booked"] += e["result"] == "booked"
    by_script = [{"label": names.get(k, f"Script #{k}"), **v, "rate": _rate(v["answered"], v["dials"]),
                  "book_rate": _rate(v["booked"], v["dials"]), "thin": v["dials"] < THIN}
                 for k, v in sorted(sc.items(), key=lambda kv: -kv[1]["dials"])]

    return {
        "start": d_start.isoformat(), "end": d_end.isoformat(), "thin_below": THIN,
        "funnel": funnel, "hours": hours, "days": days, "by_industry": by_industry,
        "by_number": by_number, "by_script": by_script if len(by_script) >= 2 else [],
    }
