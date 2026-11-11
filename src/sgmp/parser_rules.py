"""Deterministic baseline: plain-English question -> allow-listed query dict.

No model, no network. Every rule is written down here so a planner can see why a
question was read the way it was.
"""
import re

from .dsl import DEFAULT_RADIUS, QueryError, names, validate
from .vocab import ALL_PLANNING_AREAS, LAND_USE_GROUPS

UNSAFE = [
    r"\b(drop|delete|insert|update|alter|truncate|grant|exec|execute|attach|pragma)\b",
    r";", r"--", r"\bignore\b.*\binstructions?\b", r"\bselect\b.*\bfrom\b",
    r"\b(rezone|rezoned|modify|change|edit|remove|overwrite|set)\b",
]
OUT_OF_SCOPE = [
    r"\bprices?\b", r"\bpsf\b", r"\bcosts?\b", r"\brents?\b", r"\bown(s|er|ers|ership)?\b",
    r"\bpopulation\b", r"\bresidents\b", r"\bweather\b", r"\btraffic\b", r"\bforecast\b",
    r"\bwill\b", r"\bnext master plan\b", r"\b20[3-9]\d\b", r"\btenants?\b", r"\bvaluation\b",
    r"\btransactions?\b", r"\bbuilding heights?\b", r"\bpeople\b", r"\blive\b",
    r"\bhouseholds?\b",
]
GPR_CMPS = [
    ("at least", ">="), ("no less than", ">="), (">=", ">="), ("minimum of", ">="),
    ("at most", "<="), ("no more than", "<="), ("<=", "<="), ("maximum of", "<="),
    ("above", ">"), ("over", ">"), ("more than", ">"), ("greater than", ">"),
    ("higher than", ">"), ("exceeding", ">"), (">", ">"),
    ("below", "<"), ("under", "<"), ("less than", "<"), ("lower than", "<"), ("<", "<"),
    ("equal to", "="), ("exactly", "="), ("=", "="), ("of", "="),
]
NUM = r"(\d+(?:\.\d+)?)"


def refuse(reason):
    return {"op": "refuse", "reason": reason}


def _find_name(text, candidates, after=""):
    """Longest candidate name found in text (optionally followed by `after`)."""
    best = None
    for c in candidates:
        if re.search(r"\b" + re.escape(c.lower()) + r"\b" + after, text):
            if best is None or len(c) > len(best):
                best = c
    return best


def parse(question):
    t = " ".join(question.lower().replace("-", " ").split())
    raw = question.lower()
    for p in UNSAFE:
        if re.search(p, raw if p in (r";", r"--") else t):
            return refuse("read-only assistant: this looks like a request to change data or run code")
    for p in OUT_OF_SCOPE:
        if re.search(p, t):
            return refuse("out of scope: only Master Plan 2025 zoning, GPR and parcel area are available")
    pas, szs, sts = names()
    q = {}
    # station: a known name followed by "mrt" or "station"
    st = _find_name(t, sts, after=r"\s+(mrt|station)")
    if st:
        m = re.search(NUM + r"\s*(km|kilometres?|kilometers?|m|metres?|meters?)\b", t)
        radius = DEFAULT_RADIUS
        if m:
            radius = float(m.group(1)) * (1000 if m.group(2).startswith("k") else 1)
        q["near"] = {"station": st, "radius_m": radius}
    elif re.search(r"\b(mrt|station)\b", t):
        return refuse("that MRT station is not in this extract (stations in "
                      "BISHAN and DOWNTOWN CORE only)")
    sz = _find_name(t, szs, after=r"\s+subzone")
    pa = _find_name(t, pas)
    bare = None if st else _find_name(t, szs)
    if not sz and pa and bare and len(bare) > len(pa) and pa.lower() in bare.lower():
        sz = bare  # e.g. "Bishan East" is a subzone, not the Bishan planning area
    if pa and not sz and not re.search(re.escape(pa.lower()) + r"\s+(mrt|station)", t):
        q["planning_area"] = pa
    if sz:
        q["subzone"] = sz
    elif bare and "planning_area" not in q:
        q["subzone"] = bare
    if not any(k in q for k in ("near", "planning_area", "subzone")):
        other = _find_name(t, set(ALL_PLANNING_AREAS) - pas)
        if other:
            return refuse(f"{other} is not in this extract (only BISHAN and DOWNTOWN CORE)")
        return refuse("please name a planning area, subzone or MRT station in the extract")
    # land use: longest phrases first, each span consumed once
    rest, lus = t, set()
    for phrase, codes in LAND_USE_GROUPS:
        if re.search(r"\b" + re.escape(phrase), rest):
            lus.update(codes)
            rest = re.sub(r"\b" + re.escape(phrase) + r"\w*", " ", rest)
    if lus:
        q["land_use"] = sorted(lus)
    # GPR threshold
    m = re.search(r"\b(gpr|plot ratio)\b(.{0,40}?)" + NUM, t)
    if m:
        seg = m.group(2)
        for phrase, cmp in GPR_CMPS:
            if phrase in seg:
                q["gpr"] = {"cmp": cmp, "value": float(m.group(3))}
                break
    # operation
    units = r"\b(sqm|m2|square met\w*|ha|hectares?)\b"
    if re.search(r"\b(breakdown|mix|composition|split|by land use|by zoning)\b", t):
        q["op"] = "breakdown"
    elif re.search(units, t):
        q["op"] = "total_area"
    elif re.search(r"\b(how many|number of|count|no\.? of)\b", t):
        q["op"] = "count"
    elif re.search(r"\b(how much|total|area of|land area|how big)\b", t):
        q["op"] = "total_area"
    else:
        q["op"] = "list"
        if re.search(r"\b(largest|biggest)\b", t):
            q["sort"] = "area_desc"
        elif re.search(r"\bhighest (gpr|plot ratio)\b", t):
            q["sort"] = "gpr_desc"
        m = re.search(r"\b(?:top\s+)?(\d+)\s+(?:largest|biggest|parcels|sites|plots)\b", t) or \
            re.search(r"\btop\s+(\d+)\b", t)
        if m:
            q["limit"] = int(m.group(1))
    try:
        return validate(q)
    except QueryError as e:
        return refuse(str(e))
