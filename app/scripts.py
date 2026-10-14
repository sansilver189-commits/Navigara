"""Scripts page: call scripts, objection answers and text-message scripts."""
from fastapi import APIRouter, Depends, HTTPException

from .db import get_db, get_setting, set_setting
from .util import utc_now

router = APIRouter()
KINDS = ("call", "objection", "sms")

STARTER_CALL = """<h2>Opener</h2>
<p>Hi, this is <mark>[your name]</mark> from Navigara. I'll be quick - is now a bad time?</p>
<h2>Why I'm calling</h2>
<p>We work with engineering leaders at companies like [Business] that are rolling out AI tools such as Copilot or ChatGPT.</p>
<p><b>Quick question: do you know if the money you're spending on AI tools is actually paying off?</b></p>
<hr data-split>
<h2>What we do</h2>
<p>Navigara shows you, team by team, where AI is saving time and where it isn't - so you can see the return and decide where to invest.</p>
<p><mark style="background-color:#bbf7d0">Privacy:</mark> it's deployed privately in your own environment, and only AI models analyse the data - no people read it.</p>
<h2>The ask</h2>
<p>Would you be open to a 20-minute look next week? <b>Tuesday or Thursday?</b></p>
<hr data-split>
<h2>If they're technical</h2>
<p>It's built on OpenTelemetry, so it plugs into what you already collect. Runs inside your environment; only the LLMs see the data.</p>
<h2>Before hanging up</h2>
<p>Confirm the time, their email, and who else should join.</p>"""

STARTER_OBJECTION = """<p>That makes sense - most teams we talk to have something.</p>
<p><b>Can I ask: what does it tell you about whether AI is actually paying off?</b> <i>(pause, listen)</i></p>
<p>Most tools track <i>usage</i> - who uses Copilot and how often. Navigara measures the <b>result</b>: time saved and impact per team, privately in your own environment.</p>
<p>Worth 20 minutes to see if it fills a gap?</p>"""


def seed_starters(conn):
    """Adds the starter script once. Deleting it later does not bring it back."""
    if get_setting(conn, "scripts_seeded"):
        return
    now = utc_now()
    conn.execute("INSERT INTO scripts(kind, name, body, in_use, created_at, updated_at) VALUES('call', ?, ?, 1, ?, ?)",
                 ("ROI pitch (starter - edit me)", STARTER_CALL, now, now))
    conn.execute("INSERT INTO scripts(kind, name, body, created_at, updated_at) VALUES('objection', ?, ?, ?, ?)",
                 ("We already have a tool for that", STARTER_OBJECTION, now, now))
    set_setting(conn, "scripts_seeded", "1")


def _get(conn, sid):
    row = conn.execute("SELECT * FROM scripts WHERE id = ?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "Script not found")
    return row


@router.get("/api/scripts")
def list_scripts(conn=Depends(get_db)):
    return [dict(r) for r in conn.execute("SELECT * FROM scripts ORDER BY archived, kind, in_use DESC, name")]


@router.get("/api/scripts/active")
def active(conn=Depends(get_db)):
    """What the Dialer shows: the call script in use, and the ticked objection answers."""
    script = conn.execute("SELECT id, name, body FROM scripts WHERE kind = 'call' AND in_use = 1 AND archived = 0").fetchone()
    objections = conn.execute("SELECT id, name, body FROM scripts WHERE kind = 'objection' AND show_in_panel = 1 "
                              "AND archived = 0 ORDER BY name").fetchall()
    return {"script": dict(script) if script else None, "objections": [dict(o) for o in objections]}


@router.post("/api/scripts")
def create(body: dict, conn=Depends(get_db)):
    kind = body.get("kind")
    if kind not in KINDS:
        raise HTTPException(400, "Unknown kind")
    now = utc_now()
    sid = conn.execute("INSERT INTO scripts(kind, name, body, created_at, updated_at) VALUES(?, ?, ?, ?, ?)",
                       (kind, (body.get("name") or "Untitled").strip()[:120], body.get("body") or "", now, now)).lastrowid
    if kind == "call" and not conn.execute("SELECT 1 FROM scripts WHERE kind = 'call' AND in_use = 1").fetchone():
        conn.execute("UPDATE scripts SET in_use = 1 WHERE id = ?", (sid,))
    conn.commit()
    return dict(_get(conn, sid))


@router.put("/api/scripts/{sid}")
def update(sid: int, body: dict, conn=Depends(get_db)):
    row = _get(conn, sid)
    conn.execute("UPDATE scripts SET name = ?, body = ?, show_in_panel = ?, updated_at = ? WHERE id = ?",
                 ((body.get("name") or row["name"]).strip()[:120], body.get("body", row["body"]),
                  1 if body.get("show_in_panel", row["show_in_panel"]) else 0, utc_now(), sid))
    conn.commit()
    return dict(_get(conn, sid))


@router.post("/api/scripts/{sid}/use")
def use(sid: int, conn=Depends(get_db)):
    row = _get(conn, sid)
    if row["kind"] != "call" or row["archived"]:
        raise HTTPException(400, "Only an active call script can be put in use")
    conn.execute("UPDATE scripts SET in_use = 0 WHERE kind = 'call'")
    conn.execute("UPDATE scripts SET in_use = 1 WHERE id = ?", (sid,))
    conn.commit()
    return {"ok": True}


@router.post("/api/scripts/{sid}/archive")
def archive(sid: int, body: dict, conn=Depends(get_db)):
    _get(conn, sid)
    flag = 1 if body.get("archived", True) else 0
    conn.execute("UPDATE scripts SET archived = ?, in_use = CASE WHEN ? = 1 THEN 0 ELSE in_use END, updated_at = ? "
                 "WHERE id = ?", (flag, flag, utc_now(), sid))
    conn.commit()
    return {"ok": True}


@router.delete("/api/scripts/{sid}")
def delete(sid: int, conn=Depends(get_db)):
    """Removes the script. Past calls keep their script number, so Analytics still counts them."""
    _get(conn, sid)
    conn.execute("DELETE FROM scripts WHERE id = ?", (sid,))
    conn.commit()
    return {"ok": True}
