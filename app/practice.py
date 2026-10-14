"""Practice mode: fills a throwaway database with made-up companies and contacts.

Every company and person is invented. Phone numbers use 555-0100..0199, a range reserved
for fiction that never rings a real phone.
"""
import random
from datetime import datetime, timedelta, timezone

from .config import DB_PATH

COMPANIES = [
    # (name, industry, employees, engineers, keywords)
    ("Brightline Retail Group", "Retail", 42000, 900, "e-commerce, generative ai, copilot"),
    ("Harborview Insurance", "Insurance", 15000, 1200, "claims automation, machine learning"),
    ("Northgate Foods", "Food & Beverages", 9000, 260, "supply chain"),
    ("Summit Capital Bank", "Banking", 28000, 3200, "digital banking, ai, openai"),
    ("Pioneer Industrial Works", "Machinery", 12000, 450, "manufacturing, iot"),
    ("Cobalt Logistics", "Logistics & Supply Chain", 7000, 380, "routing, genai"),
    ("Evergreen Health Systems", "Hospital & Health Care", 33000, 1500, "ehr, ai"),
    ("Lumen Apparel Co", "Apparel & Fashion", 18000, 300, "omnichannel retail"),
    ("Redwood Energy Partners", "Oil & Energy", 11000, 600, "copilot, data platform"),
    ("Atlas Consumer Brands", "Consumer Goods", 21000, 700, "generative ai, chatgpt"),
    ("Keystone Auto Parts", "Automotive", 6000, 150, ""),
    ("Meridian Software Labs", "Computer Software", 2500, 1400, "saas, llm, machine learning"),
    ("Quantix Cloud", "Information Technology & Services", 900, 600, "cloud, ai"),
    ("Tiny Corner Bakery", "Food & Beverages", 12, None, ""),
    ("Bluewater Pharma", "Pharmaceuticals", 8000, 220, "ai, drug discovery"),
    ("Granite Construction Supply", "Construction", 4000, 80, ""),
    ("Velocity Airlines", "Airlines/Aviation", 25000, 1100, "copilot, chatgpt"),
    ("Orchard Grocery Stores", "Retail", 60000, 800, "genai"),
    ("Gigantic Search Co", "Internet", 150000, 30000, ""),
    ("Northwind Consulting", "Management Consulting", 3000, None, ""),
]
FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Drew",
         "Sam", "Robin", "Cameron", "Reese", "Skyler", "Parker"]
LAST = ["Martinez", "Johnson", "Lee", "Patel", "Nguyen", "Smith", "Garcia", "Brown", "Kim",
        "Davis", "Lopez", "Wilson", "Clark", "Hall"]
TITLES = ["CTO", "VP of Engineering", "Head of Engineering", "Chief AI Officer", "CIO",
          "Director of Engineering", "SVP Software Engineering", "Head of Developer Productivity",
          "VP Marketing", "Engineering Manager", "Chief Digital Officer", "Director of AI & Machine Learning"]
PLACES = [("Austin", "TX", "512"), ("Dallas", "TX", "214"), ("Chicago", "IL", "312"),
          ("Atlanta", "GA", "404"), ("Denver", "CO", "303"), ("Phoenix", "AZ", "602"),
          ("Boston", "MA", "617"), ("Seattle", "WA", "206")]


def make_rows(n=70, seed=42):
    rng = random.Random(seed)
    rows, used = [], set()
    for i in range(n):
        company, industry, employees, engineers, keywords = rng.choice(COMPANIES)
        city, state, ac = rng.choice(PLACES)
        while True:
            line = rng.randint(100, 199)
            if (ac, line) not in used:
                used.add((ac, line))
                break
        first, last = rng.choice(FIRST), rng.choice(LAST)
        rows.append({
            "source_id": f"practice-{i}",
            "contact_name": f"{first} {last}",
            "title": rng.choice(TITLES),
            "company": company,
            "industry": industry,
            "employees": str(employees),
            "engineers": str(engineers) if engineers and rng.random() < 0.7 else "",
            "email": f"{first}.{last}{i}@example.com".lower(),
            "city": city, "state": state,
            "country": "Canada" if rng.random() < 0.05 else "United States",
            "keywords": keywords,
            "phone": None if rng.random() < 0.03 else f"+1{ac}5550{line}",
            "phone_type": rng.choice(["direct", "mobile", "company", "company"]),
        })
    return rows


def seed(conn):
    from .leads import import_facts
    import_facts(conn, make_rows(), "Practice leads (made up)", kind="practice")
    _seed_history(conn)


def _seed_history(conn):
    """A month of made-up past calls on extra made-up leads, so Analytics has something to show."""
    from .dialer import PRACTICE_NUMBERS
    from .leads import import_facts
    from .util import local_tz

    rows = make_rows(n=160, seed=99)
    for r in rows:
        r["source_id"] = "history-" + r["source_id"]
        r["email"] = "h." + r["email"]
        r["contact_name"] = r["contact_name"] + " Jr"
    import_facts(conn, rows, "Practice call history (made up)", kind="practice")
    ids = [r[0] for r in conn.execute(
        "SELECT l.id FROM leads l JOIN batches b ON b.id = l.batch_id "
        "WHERE b.name LIKE 'Practice call history%' AND l.status = 'ready'")]
    # A second (made-up) script, so Analytics can compare two scripts.
    first = conn.execute("SELECT id FROM scripts WHERE kind = 'call' ORDER BY id LIMIT 1").fetchone()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    second = conn.execute(
        "INSERT INTO scripts(kind, name, body, created_at, updated_at) VALUES('call', ?, ?, ?, ?)",
        ("Technical pitch (practice)", "<h2>Opener</h2><p>Hi, quick one about OpenTelemetry and AI at [Business].</p>",
         stamp, stamp)).lastrowid
    script_ids = [first[0], second] if first else [second]
    rng = random.Random(3)
    tz = local_tz()
    now = datetime.now(tz) - timedelta(days=1)
    today = datetime.now(tz).date()
    for lead_id in ids:
        for attempt in range(2):  # a miss gets its second try, so history leads are finished
            day = today - timedelta(days=rng.randint(1, 30))
            while day.weekday() >= 5:  # weekdays only
                day = today - timedelta(days=rng.randint(1, 30))
            hour = rng.choice([8, 9, 9, 10, 10, 11, 13, 14, 14, 15, 16, 16])
            when = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), tzinfo=tz)
            number = rng.choice(PRACTICE_NUMBERS)
            # Mornings and late afternoons answer more; the 404 number "stops working" this week.
            p_answer = 0.45 if hour in (9, 10, 16) else 0.25
            if number.startswith("+1404") and (today - day).days <= 7:
                p_answer = 0.05
            if rng.random() < p_answer:
                result = rng.choice(["not_interested", "not_interested", "gatekeeper", "call_later",
                                     "send_info", "booked"])
            else:
                result = rng.choice(["no_answer", "no_answer", "left_voicemail"])
            conn.execute(
                "INSERT INTO call_events(lead_id, result, source, from_number, duration_sec, script_id, created_at) "
                "VALUES(?, ?, 'dialer', ?, ?, ?, ?)",
                (lead_id, result, number, rng.randint(5, 240), rng.choice(script_ids),
                 when.astimezone(timezone.utc).isoformat(timespec="seconds")),
            )
            if result == "booked":
                if rng.random() < 0.7:
                    conn.execute("INSERT INTO call_events(lead_id, result, source, created_at) VALUES(?, 'showed', 'manual', ?)",
                                 (lead_id, min(when + timedelta(days=3), now).astimezone(timezone.utc).isoformat(timespec="seconds")))
                    if rng.random() < 0.4:
                        conn.execute("INSERT INTO call_events(lead_id, result, source, created_at) VALUES(?, 'signed', 'manual', ?)",
                                     (lead_id, min(when + timedelta(days=10), now).astimezone(timezone.utc).isoformat(timespec="seconds")))
                break
            if result not in ("no_answer", "left_voicemail", "gatekeeper"):
                break
    conn.commit()


def reset_file():
    """Throw away the old practice database so every practice session starts fresh."""
    for suffix in ("", "-wal", "-shm"):
        p = DB_PATH.with_name(DB_PATH.name + suffix)
        if p.exists():
            p.unlink()
