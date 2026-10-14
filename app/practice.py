"""Practice mode: fills a throwaway database with made-up businesses.

Phone numbers use the 555-0100..0199 range, which is reserved for fiction and never
rings a real business.
"""
import json
import random
from datetime import datetime, timedelta, timezone

from .config import DB_PATH
from .util import utc_now

TRADES = {
    "Plumber": ["Plumbing", "Rooter & Drain", "Pipe Pros"],
    "HVAC contractor": ["Heating & Air", "Comfort HVAC", "Cooling Co"],
    "Roofing contractor": ["Roofing", "Roof Masters", "Shingle Works"],
    "Electrician": ["Electric", "Wiring Co", "Power Services"],
    "Landscaper": ["Landscaping", "Lawn & Garden", "Yard Care"],
    "Auto repair shop": ["Auto Repair", "Motors", "Garage"],
    "Dentist": ["Family Dental", "Smiles", "Dental Care"],
    "Hair salon": ["Hair Studio", "Salon", "Cuts & Color"],
}
OWNERS = ["Martinez", "Johnson", "Lee", "Patel", "Nguyen", "Smith", "Garcia", "Brown",
          "Kim", "Davis", "Lopez", "Wilson", "Clark", "Hall", "Young", "King", "Wright",
          "Scott", "Green", "Baker", "Adams", "Nelson", "Hill", "Rivera", "Campbell"]
CITIES = [("Austin", "TX", "512"), ("Dallas", "TX", "214"), ("Houston", "TX", "713"),
          ("Phoenix", "AZ", "602"), ("Denver", "CO", "303"), ("Atlanta", "GA", "404")]
STREETS = ["Main St", "Oak Ave", "Elm St", "Cedar Ln", "Park Blvd", "Lake Dr", "Hill Rd"]


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _fake_review_facts(rng, now):
    """Pretend data, shaped like what the scraper will save."""
    count = rng.choice([0, 2, 5, 9, 14, 22, 35, 48, 60, 85, 120, 240, 600])
    rating = round(rng.uniform(3.2, 5.0), 1) if count else None
    # How active is the page? Recent = lots of fresh reviews.
    activity = rng.choice(["hot", "warm", "quiet", "dead"])
    max_age = {"hot": 60, "warm": 180, "quiet": 420, "dead": 900}[activity]
    min_age = {"hot": 1, "warm": 20, "quiet": 120, "dead": 400}[activity]
    dates = sorted((now - timedelta(days=rng.randint(min_age, max_age)) for _ in range(min(count, 20))),
                   reverse=True)
    replies = [d + timedelta(days=rng.randint(0, 4)) for d in dates if rng.random() < (0.6 if activity == "hot" else 0.2)]
    stars = {}
    if count:
        five = int(count * max(0.0, min(1.0, (rating - 3) / 2)))
        stars = {"5": five, "4": int((count - five) * 0.5), "3": 0, "2": 0, "1": 0}
        stars["1"] = count - sum(stars.values())
    return {
        "review_count": count,
        "rating": rating,
        "star_counts": stars,
        "review_dates": [_iso(d) for d in dates],
        "owner_reply_dates": [_iso(d) for d in replies],
        "permanently_closed": rng.random() < 0.04,
        "has_website": rng.random() < 0.5,
    }


def seed(conn, n=80):
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    stamp = utc_now()
    cur = conn.execute(
        "INSERT INTO batches(kind, name, details, found, checked, qualified, created_at) "
        "VALUES('practice', 'Practice leads (made up)', '{}', ?, ?, 0, ?)",
        (n, n, stamp),
    )
    batch_id = cur.lastrowid
    used_numbers = set()
    for i in range(n):
        category, words = rng.choice(list(TRADES.items()))
        city, state, ac = rng.choice(CITIES)
        while True:
            line = rng.randint(100, 199)
            if (ac, line) not in used_numbers:
                used_numbers.add((ac, line))
                break
        phone = None if rng.random() < 0.03 else f"+1{ac}5550{line}"
        facts = _fake_review_facts(rng, now)
        name = f"{rng.choice(OWNERS)} {rng.choice(words)}"
        conn.execute(
            """INSERT INTO leads(batch_id, place_id, name, phone, category, address, city, state,
                   website, maps_url, rating, review_count, review_facts, status, created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 'pending', ?, ?)""",
            (batch_id, f"practice-{i}", name, phone, category,
             f"{rng.randint(100, 9999)} {rng.choice(STREETS)}", city, state,
             f"https://example.com/{i}" if facts["has_website"] else None,
             facts["rating"], facts["review_count"], json.dumps(facts), stamp, stamp),
        )
    conn.commit()


def reset_file():
    """Throw away the old practice database so every practice session starts fresh."""
    for suffix in ("", "-wal", "-shm"):
        p = DB_PATH.with_name(DB_PATH.name + suffix)
        if p.exists():
            p.unlink()
