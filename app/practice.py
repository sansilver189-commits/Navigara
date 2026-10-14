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
    # A few past results so the Leads page has something to show.
    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    ids = [r[0] for r in conn.execute("SELECT id FROM leads WHERE status = 'ready'").fetchall()]
    for lead_id in rng.sample(ids, min(12, len(ids))):
        when = now - timedelta(days=rng.randint(1, 10), hours=rng.randint(0, 8))
        conn.execute(
            "INSERT INTO call_events(lead_id, result, source, created_at) VALUES(?, ?, 'dialer', ?)",
            (lead_id, rng.choice(["no_answer", "no_answer", "not_interested", "booked", "call_later"]),
             when.isoformat(timespec="seconds")),
        )
    conn.commit()


def reset_file():
    """Throw away the old practice database so every practice session starts fresh."""
    for suffix in ("", "-wal", "-shm"):
        p = DB_PATH.with_name(DB_PATH.name + suffix)
        if p.exists():
            p.unlink()
