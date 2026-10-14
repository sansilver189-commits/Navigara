"""Leads page: list, search, filters, CSV import/export, scoring, and manual results."""
import csv
import io
import json
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from .db import get_db
from .importer import parse_csv
from .results import RESULTS
from .scoring import load_settings, score_lead
from .util import pretty_phone, utc_now

router = APIRouter()

LEAD_COLUMNS = ["source_id", "name", "contact_name", "title", "phone", "phone_type", "email",
                "linkedin", "industry", "employees", "engineers", "city", "state", "country", "website"]

# Latest result per lead (ignored mistakes do not count).
LIST_SQL = """
SELECT l.*, b.name AS batch_name, e.result AS last_result, e.created_at AS last_call
FROM leads l
LEFT JOIN batches b ON b.id = l.batch_id
LEFT JOIN (
    SELECT lead_id, result, created_at,
           ROW_NUMBER() OVER (PARTITION BY lead_id ORDER BY created_at DESC, id DESC) AS rn
    FROM call_events WHERE ignored = 0
) e ON e.lead_id = l.id AND e.rn = 1
WHERE b.deleted_at IS NULL
"""


def _to_int(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _apply_score(conn, lead_id, facts, settings):
    r = score_lead(facts, settings)
    conn.execute(
        "UPDATE leads SET status=?, score=?, grade=?, skip_reason=?, pitch=?, score_detail=?, updated_at=? WHERE id=?",
        (r["status"], r["score"], r["grade"], r["skip_reason"], r["pitch"], json.dumps(r["detail"]),
         utc_now(), lead_id),
    )
    return r


def _filtered(conn, q="", grade="", status="", result="", batch="", limit=None):
    sql, args = LIST_SQL, []
    if q:
        digits = re.sub(r"\D", "", q)
        like = f"%{q.lower()}%"
        cond = "lower(l.name) LIKE ? OR lower(coalesce(l.contact_name,'')) LIKE ? OR lower(coalesce(l.title,'')) LIKE ?"
        args += [like, like, like]
        if len(digits) >= 3:
            cond += " OR l.phone LIKE ?"
            args.append(f"%{digits}%")
        sql += f" AND ({cond})"
    if grade:
        sql += " AND l.grade = ?"
        args.append(grade)
    if status:
        sql += " AND l.status = ?"
        args.append(status)
    if result == "none":
        sql += " AND e.result IS NULL"
    elif result:
        sql += " AND e.result = ?"
        args.append(result)
    if batch:
        sql += " AND l.batch_id = ?"
        args.append(int(batch))
    sql += " ORDER BY (l.status = 'ready') DESC, l.score DESC NULLS LAST, l.id"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, args).fetchall()


@router.get("/api/results")
def results():
    return RESULTS


@router.get("/api/leads/summary")
def summary(conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT l.status, COUNT(*) n FROM leads l LEFT JOIN batches b ON b.id = l.batch_id "
        "WHERE b.deleted_at IS NULL GROUP BY l.status"
    ).fetchall()
    counts = {r["status"]: r["n"] for r in rows}
    return {"ready": counts.get("ready", 0), "low": counts.get("low", 0),
            "skipped": counts.get("skipped", 0), "total": sum(counts.values()),
            "ready_score": load_settings()["ready_score"]}


@router.get("/api/leads")
def list_leads(q: str = "", grade: str = "", status: str = "", result: str = "", batch: str = "",
               conn=Depends(get_db)):
    limit = 500
    rows = _filtered(conn, q, grade, status, result, batch, limit=limit + 1)
    out = [{
        "id": r["id"], "company": r["name"], "contact": r["contact_name"], "title": r["title"],
        "phone": r["phone"], "phone_pretty": pretty_phone(r["phone"]), "phone_type": r["phone_type"],
        "score": r["score"], "grade": r["grade"], "status": r["status"], "skip_reason": r["skip_reason"],
        "pitch": r["pitch"], "last_result": r["last_result"], "last_call": r["last_call"],
    } for r in rows[:limit]]
    return {"leads": out, "more": len(rows) > limit}


@router.get("/api/leads/export")
def export(q: str = "", grade: str = "", status: str = "", result: str = "", batch: str = "",
           conn=Depends(get_db)):
    rows = _filtered(conn, q, grade, status, result, batch)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Company", "Contact", "Title", "Phone", "Phone type", "Email", "LinkedIn", "Industry",
                "Employees", "Engineers", "City", "State", "Country", "Score", "Grade", "Status",
                "Skip reason", "Pitch", "Last result", "Last call (UTC)", "Batch"])
    for r in rows:
        w.writerow([r["name"], r["contact_name"], r["title"], pretty_phone(r["phone"]), r["phone_type"],
                    r["email"], r["linkedin"], r["industry"], r["employees"], r["engineers"], r["city"],
                    r["state"], r["country"], r["score"], r["grade"], r["status"], r["skip_reason"],
                    r["pitch"], RESULTS.get(r["last_result"], r["last_result"]), r["last_call"],
                    r["batch_name"]])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="navigara-leads.csv"'})


@router.get("/api/leads/{lead_id}")
def lead_detail(lead_id: int, conn=Depends(get_db)):
    r = conn.execute("SELECT l.*, b.name AS batch_name FROM leads l LEFT JOIN batches b ON b.id = l.batch_id "
                     "WHERE l.id = ?", (lead_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Lead not found")
    events = conn.execute("SELECT * FROM call_events WHERE lead_id = ? ORDER BY created_at DESC, id DESC",
                          (lead_id,)).fetchall()
    lead = {k: r[k] for k in r.keys() if k not in ("facts", "score_detail", "review_facts")}
    lead["phone_pretty"] = pretty_phone(r["phone"])
    lead["score_detail"] = json.loads(r["score_detail"] or "[]")
    return {"lead": lead, "events": [dict(e) for e in events]}


@router.post("/api/leads/{lead_id}/result")
def set_result(lead_id: int, body: dict, conn=Depends(get_db)):
    """A result set from the Leads page is bookkeeping (source 'manual'), not a dial."""
    result = body.get("result")
    if result not in RESULTS:
        raise HTTPException(400, "Unknown result")
    if not conn.execute("SELECT 1 FROM leads WHERE id = ?", (lead_id,)).fetchone():
        raise HTTPException(404, "Lead not found")
    conn.execute("INSERT INTO call_events(lead_id, result, source, note, created_at) VALUES(?, ?, 'manual', ?, ?)",
                 (lead_id, result, (body.get("note") or "").strip() or None, utc_now()))
    conn.commit()
    return {"ok": True}


@router.post("/api/call-events/{event_id}/ignore")
def ignore_event(event_id: int, body: dict, conn=Depends(get_db)):
    """Mark a mistaken result as ignored (or bring it back). Nothing is deleted."""
    ignored = 1 if body.get("ignored", True) else 0
    cur = conn.execute("UPDATE call_events SET ignored = ?, ignored_at = ? WHERE id = ?",
                       (ignored, utc_now() if ignored else None, event_id))
    conn.commit()
    if not cur.rowcount:
        raise HTTPException(404, "Not found")
    return {"ok": True}


def _find_duplicate(conn, f):
    """Same person already in the system? Check the strongest match first."""
    checks = [
        ("source_id = ?", f.get("source_id")),
        ("lower(email) = ?", (f.get("email") or "").lower()),
        ("lower(linkedin) = ?", (f.get("linkedin") or "").lower().rstrip("/")),
    ]
    for cond, val in checks:
        if val:
            row = conn.execute(f"SELECT id FROM leads WHERE {cond}", (val,)).fetchone()
            if row:
                return row["id"]
    name, company = (f.get("contact_name") or "").lower(), (f.get("company") or "").lower()
    if name and company:
        row = conn.execute("SELECT id FROM leads WHERE lower(contact_name) = ? AND lower(name) = ?",
                           (name, company)).fetchone()
        if row:
            return row["id"]
    if f.get("phone") and not name:
        row = conn.execute("SELECT id FROM leads WHERE phone = ? AND coalesce(contact_name, '') = ''",
                           (f["phone"],)).fetchone()
        if row:
            return row["id"]
    return None


def import_facts(conn, rows, batch_name, kind="csv"):
    settings = load_settings()
    now = utc_now()
    batch_id = conn.execute("INSERT INTO batches(kind, name, details, found, created_at) VALUES(?, ?, '{}', ?, ?)",
                            (kind, batch_name, len(rows), now)).lastrowid
    stats = {"rows": len(rows), "added": 0, "duplicates": 0, "ready": 0, "low": 0, "skipped": 0}
    for f in rows:
        if f.get("linkedin"):
            f["linkedin"] = f["linkedin"].rstrip("/")
        if _find_duplicate(conn, f):
            stats["duplicates"] += 1
            continue
        values = {c: f.get(c) or None for c in LEAD_COLUMNS}
        values["name"] = f.get("company") or "(no company)"
        values["employees"] = _to_int(f.get("employees"))
        values["engineers"] = _to_int(f.get("engineers"))
        cols = list(values) + ["batch_id", "facts", "created_at", "updated_at"]
        lead_id = conn.execute(
            f"INSERT INTO leads({', '.join(cols)}) VALUES({', '.join('?' * len(cols))})",
            [*values.values(), batch_id, json.dumps(f), now, now],
        ).lastrowid
        r = _apply_score(conn, lead_id, f, settings)
        stats["added"] += 1
        stats[r["status"]] += 1
    if stats["added"]:
        conn.execute("UPDATE batches SET checked = ?, qualified = ? WHERE id = ?",
                     (stats["added"], stats["ready"], batch_id))
    else:
        conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))  # nothing new: no empty import
        batch_id = None
    conn.commit()
    stats["batch_id"] = batch_id
    return stats


@router.post("/api/leads/import")
async def import_csv(file: UploadFile, conn=Depends(get_db)):
    raw = await file.read()
    rows = parse_csv(raw)
    if not rows:
        raise HTTPException(400, "No rows found. Is this a CSV file with a header row?")
    return import_facts(conn, rows, file.filename or "CSV upload")


@router.post("/api/leads/rescore")
def rescore(conn=Depends(get_db)):
    """Re-score every lead from its saved facts using the current scoring.toml."""
    try:
        settings = load_settings()
    except Exception as e:
        raise HTTPException(400, f"scoring.toml has a mistake in it: {e}")
    n = 0
    for r in conn.execute("SELECT id, facts FROM leads").fetchall():
        _apply_score(conn, r["id"], json.loads(r["facts"] or "{}"), settings)
        n += 1
    conn.commit()
    return {"rescored": n}


@router.get("/api/batches")
def batches(conn=Depends(get_db)):
    rows = conn.execute("SELECT id, kind, name, found, checked, qualified, created_at FROM batches "
                        "WHERE deleted_at IS NULL ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]
