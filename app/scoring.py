"""Lead scoring. Every number comes from scoring.toml in the project folder.

Order: cheap hard drops -> skips (with a reason) -> points. The facts a score is built from
are stored on the lead, so changing scoring.toml and re-scoring needs no re-import.
"""
import re
import tomllib

from .config import ROOT

SETTINGS_FILE = ROOT / "scoring.toml"


def load_settings() -> dict:
    with open(SETTINGS_FILE, "rb") as f:
        return tomllib.load(f)


def _norm(text) -> str:
    """Lowercase, unify 'Vice President'/'SVP' to 'vp', drop punctuation, pad with spaces."""
    t = str(text or "").lower().replace("&", " and ")
    t = re.sub(r"\b(senior |executive |assistant )?vice[- ]president\b", "vp", t)
    t = re.sub(r"\b(svp|evp|avp)\b", "vp", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return f" {t.strip()} "


def _has(text_norm: str, phrase: str) -> bool:
    return _norm(phrase) in text_norm


def _any(text_norm: str, phrases) -> list[str]:
    return [p for p in phrases if _has(text_norm, p)]


def _to_int(value):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def title_level(title: str, s: dict) -> str | None:
    """'top', 'mid' or None (not a tech/AI leader)."""
    t = _norm(title)
    cfg = s["title"]
    if not t.strip() or _any(t, cfg["excluded"]):
        return None
    if _any(t, cfg["top_exact"]):
        return "top"
    has_area = bool(_any(t, cfg["areas"]))
    if has_area and _any(t, cfg["top_levels"]):
        return "top"
    if _any(t, cfg["mid_exact"]):
        return "mid"
    if has_area and _any(t, cfg["mid_levels"]):
        return "mid"
    return None


def industry_kind(industry: str, s: dict) -> str:
    """'tech', 'non_tech' or 'unknown'. Matched as parts of words (e.g. 'financ')."""
    low = str(industry or "").lower()
    if not low.strip():
        return "unknown"
    if any(w in low for w in s["industry"]["tech"]):
        return "tech"
    if any(w in low for w in s["industry"]["non_tech"]):
        return "non_tech"
    return "unknown"


def _band(value, bands):
    for lo, hi, pts in bands:
        if lo <= value < hi:
            return pts
    return 0


def score_lead(facts: dict, s: dict | None = None) -> dict:
    """Returns status ('ready' / 'low' / 'skipped'), score, grade, skip_reason, pitch, detail."""
    s = s or load_settings()

    def skip(reason):
        return {"status": "skipped", "score": None, "grade": None, "skip_reason": reason,
                "pitch": None, "detail": []}

    # 1. Hard drops
    if not (facts.get("company") or "").strip():
        return skip("No company name")
    if not facts.get("phone"):
        return skip("No phone number")

    # 2. Skips
    country = (facts.get("country") or "").strip().lower()
    if country and country not in s["country"]["allowed"]:
        return skip(f"Outside allowed countries ({facts.get('country')})")

    engineers = _to_int(facts.get("engineers"))
    employees = _to_int(facts.get("employees"))
    if engineers is not None:
        if engineers < s["size"]["min_engineers"]:
            return skip(f"Too small: {engineers} engineers")
    elif employees is not None:
        if employees < s["size"]["min_employees_if_engineers_unknown"]:
            return skip(f"Too small: {employees} employees")

    level = title_level(facts.get("title"), s)
    if level is None:
        return skip(f"Not a tech/AI leader: {facts.get('title') or 'no title'}")

    # 3. Points
    detail = []
    kind = industry_kind(facts.get("industry"), s)
    detail.append({
        "non_tech": ("Non-tech industry", s["industry"]["non_tech_points"]),
        "tech": ("Software/tech industry", s["industry"]["tech_points"]),
        "unknown": ("Industry unknown", s["industry"]["unknown_points"]),
    }[kind])

    if engineers is not None:
        detail.append((f"{engineers:,} engineers", _band(engineers, s["engineers"]["bands"])))
    elif employees is not None:
        detail.append((f"{employees:,} employees (engineers unknown)",
                       _band(employees, s["employees"]["bands"])))
    else:
        detail.append(("Company size unknown", 0))

    detail.append(("Top tech/AI leader title" if level == "top" else "Senior tech title",
                   s["title"]["top_points"] if level == "top" else s["title"]["mid_points"]))

    blob = _norm(" ".join(str(facts.get(k) or "") for k in ("keywords", "technologies", "title", "notes")))
    ai_hits = _any(blob, s["ai_signals"]["words"])
    # "generative ai" should not also count as "ai"
    ai_hits = [h for h in ai_hits if not any(h != o and _has(_norm(o), h) for o in ai_hits)]
    if ai_hits:
        pts = min(len(ai_hits) * s["ai_signals"]["per_word"], s["ai_signals"]["max_points"])
        detail.append((f"AI signals: {', '.join(ai_hits[:4])}", pts))

    if facts.get("phone_type") in ("direct", "mobile"):
        detail.append(("Direct/mobile number", s["phone"]["direct_points"]))

    score = min(100, sum(p for _, p in detail))
    if _any(_norm(facts.get("company")), s["big_tech"]["names"]):
        cap = s["big_tech"]["max_score"]
        if score > cap:
            detail.append((f"Big Tech: long shot, capped at {cap}", cap - score))
            score = cap

    g = s["grades"]
    grade = "A" if score >= g["A"] else "B" if score >= g["B"] else "C" if score >= g["C"] else "D"
    pitch = "Technical" if kind == "tech" else "ROI"
    return {
        "status": "ready" if score >= s["ready_score"] else "low",
        "score": score, "grade": grade, "skip_reason": None, "pitch": pitch,
        "detail": [{"label": label, "points": pts} for label, pts in detail],
    }
