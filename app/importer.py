"""Reads a CSV of leads (an Apollo export, or a simple hand-made sheet) into lead facts."""
import csv
import io
import re

from .util import normalize_phone

# Column names we understand -> our field. Compared after lowercasing and removing symbols.
ALIASES = {
    "source_id": ["apollo contact id", "contact id", "id", "person id"],
    "first_name": ["first name", "firstname"],
    "last_name": ["last name", "lastname", "surname"],
    "contact_name": ["name", "full name", "contact", "contact name", "person"],
    "title": ["title", "job title", "position", "role"],
    "company": ["company", "company name", "organization", "organization name", "account name", "business"],
    "industry": ["industry", "company industry"],
    "employees": ["employees", "employees", "number of employees", "company size", "employee count",
                  "headcount", "estimated num employees"],
    "engineers": ["engineers", "engineering headcount", "number of engineers", "engineering employees",
                  "engineering"],
    "email": ["email", "work email", "email address"],
    "linkedin": ["person linkedin url", "linkedin", "linkedin url", "linkedin profile"],
    "website": ["website", "company website", "domain"],
    "city": ["city", "company city"],
    "state": ["state", "company state", "region"],
    "country": ["country", "company country"],
    "keywords": ["keywords", "company keywords", "tags"],
    "technologies": ["technologies", "tech stack"],
    "notes": ["notes", "note", "comments"],
}
# Phone columns, best first, and what kind of number each is.
PHONE_COLUMNS = [
    ("work direct phone", "direct"), ("direct phone", "direct"), ("direct dial", "direct"),
    ("mobile phone", "mobile"), ("mobile", "mobile"), ("cell", "mobile"),
    ("phone", "unknown"), ("first phone", "unknown"), ("phone number", "unknown"),
    ("corporate phone", "company"), ("company phone", "company"), ("other phone", "unknown"),
]


def _key(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", header.lower().replace("#", "number of")).strip()


def parse_csv(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = {_key(h): h for h in (reader.fieldnames or []) if h}
    alias_map = {}
    for field, names in ALIASES.items():
        for n in names:
            if _key(n) in headers and field not in alias_map:
                alias_map[field] = headers[_key(n)]
    phone_cols = [(headers[_key(n)], kind) for n, kind in PHONE_COLUMNS if _key(n) in headers]

    rows = []
    for row in reader:
        facts = {f: (row.get(col) or "").strip() for f, col in alias_map.items()}
        if not facts.get("contact_name"):
            facts["contact_name"] = " ".join(x for x in (facts.get("first_name"), facts.get("last_name")) if x)
        facts["phone"], facts["phone_type"] = None, None
        for col, kind in phone_cols:
            p = normalize_phone(row.get(col))
            if p:
                facts["phone"], facts["phone_type"] = p, kind
                break
        if any(v for v in facts.values()):
            rows.append(facts)
    return rows
