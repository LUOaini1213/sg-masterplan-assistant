"""The allow-listed query language. Only a validated dict reaches the engine.

A query is a JSON object with these keys and nothing else:
  op            "list" | "count" | "total_area" | "breakdown" | "refuse"
  planning_area one planning area in the extract (optional)
  subzone       one subzone in the extract (optional)
  land_use      list of exact Master Plan LU_DESC codes (optional)
  gpr           {"cmp": ">"|">="|"<"|"<="|"=", "value": number} (optional)
  near          {"station": name, "radius_m": 50..2000} (optional)
  sort          "area_desc" | "gpr_desc" (list only, optional)
  limit         1..500 (list only, optional)
  reason        text (refuse only)
At least one of planning_area, subzone, near is required (a spatial scope).
"""
from .data import load
from .vocab import LAND_USE_CODES

OPS = {"list", "count", "total_area", "breakdown", "refuse"}
KEYS = {"op", "planning_area", "subzone", "land_use", "gpr", "near", "sort", "limit", "reason"}
CMPS = {">", ">=", "<", "<=", "="}
SORTS = {"area_desc", "gpr_desc"}
MAX_RADIUS = 2000
MIN_RADIUS = 50
DEFAULT_RADIUS = 400


class QueryError(ValueError):
    pass


def names():
    d = load()
    return (set(d["planning_areas"].PLN_AREA_N), set(d["subzones"].SUBZONE_N),
            set(d["stations"].STATION))


def _station_name(s):
    s = str(s).upper().strip()
    for suffix in (" MRT STATION", " MRT", " STATION"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s.strip()


def validate(q):
    if not isinstance(q, dict):
        raise QueryError("query must be an object")
    extra = set(q) - KEYS
    if extra:
        raise QueryError(f"unknown keys: {sorted(extra)}")
    op = q.get("op")
    if op not in OPS:
        raise QueryError(f"op must be one of {sorted(OPS)}")
    if op == "refuse":
        return {"op": "refuse", "reason": str(q.get("reason", ""))[:300]}
    pas, szs, sts = names()
    out = {"op": op}
    if q.get("planning_area") is not None:
        pa = str(q["planning_area"]).upper()
        if pa not in pas:
            raise QueryError(f"planning area not in extract: {pa}")
        out["planning_area"] = pa
    if q.get("subzone") is not None:
        sz = str(q["subzone"]).upper()
        if sz not in szs:
            raise QueryError(f"subzone not in extract: {sz}")
        out["subzone"] = sz
    if q.get("land_use") is not None:
        lu = q["land_use"]
        if not isinstance(lu, list) or not lu:
            raise QueryError("land_use must be a non-empty list")
        lu = sorted({str(x).upper() for x in lu})
        bad = [x for x in lu if x not in LAND_USE_CODES]
        if bad:
            raise QueryError(f"unknown land-use codes: {bad}")
        out["land_use"] = lu
    if q.get("gpr") is not None:
        g = q["gpr"]
        if not isinstance(g, dict) or set(g) != {"cmp", "value"} or g["cmp"] not in CMPS:
            raise QueryError("gpr must be {cmp, value}")
        try:
            v = float(g["value"])
        except (TypeError, ValueError):
            raise QueryError("gpr value must be a number")
        if not 0 <= v <= 30:
            raise QueryError("gpr value out of range 0..30")
        out["gpr"] = {"cmp": g["cmp"], "value": v}
    if q.get("near") is not None:
        n = q["near"]
        if not isinstance(n, dict) or set(n) - {"station", "radius_m"} or "station" not in n:
            raise QueryError("near must be {station, radius_m}")
        st = _station_name(n["station"])
        if st not in sts:
            raise QueryError(f"station not in extract: {st}")
        try:
            r = float(n.get("radius_m") or DEFAULT_RADIUS)
        except (TypeError, ValueError):
            raise QueryError("radius_m must be a number")
        if not MIN_RADIUS <= r <= MAX_RADIUS:
            raise QueryError(f"radius_m must be {MIN_RADIUS}..{MAX_RADIUS}")
        out["near"] = {"station": st, "radius_m": r}
    if not any(k in out for k in ("planning_area", "subzone", "near")):
        raise QueryError("a planning area, subzone or MRT station in the extract is required")
    if q.get("sort") is not None:
        if op != "list" or q["sort"] not in SORTS:
            raise QueryError("sort only for list, one of area_desc/gpr_desc")
        out["sort"] = q["sort"]
    if q.get("limit") is not None:
        if op != "list":
            raise QueryError("limit only for list")
        try:
            lim = int(q["limit"])
        except (TypeError, ValueError):
            raise QueryError("limit must be an integer")
        if not 1 <= lim <= 500:
            raise QueryError("limit must be 1..500")
        out["limit"] = lim
    return out


def _s(x):
    return "'" + x.replace("'", "''") + "'"


def to_sql(q):
    """Readable SQL-like rendering of a validated query, shown to the planner."""
    if q["op"] == "refuse":
        return f"-- refused: {q.get('reason', '')}"
    geom = "ST_Intersection(geom, buffer)" if "near" in q else "geom"
    sel = {
        "list": f"objectid, lu_desc, gpr, ST_Area({geom}) AS area_m2",
        "count": "COUNT(*) AS parcels",
        "total_area": f"SUM(ST_Area({geom})) AS area_m2",
        "breakdown": f"lu_desc, COUNT(*) AS parcels, SUM(ST_Area({geom})) AS area_m2",
    }[q["op"]]
    where = []
    if "planning_area" in q:
        where.append(f"planning_area = {_s(q['planning_area'])}")
    if "subzone" in q:
        where.append(f"subzone = {_s(q['subzone'])}")
    if "land_use" in q:
        where.append("lu_desc IN (" + ", ".join(_s(x) for x in q["land_use"]) + ")")
    if "gpr" in q:
        where.append(f"gpr_numeric {q['gpr']['cmp']} {q['gpr']['value']:g}"
                     "  -- non-numeric GPR (LND/EVA/SDP) excluded")
    if "near" in q:
        n = q["near"]
        where.append(f"ST_Intersects(geom, buffer)  -- buffer = {n['radius_m']:g} m around "
                     f"{n['station']} MRT (centroid of its exits)")
    sql = f"SELECT {sel}\nFROM mp2025_landuse  -- EPSG:3414, metres"
    if where:
        sql += "\nWHERE " + "\n  AND ".join(where)
    if q["op"] == "breakdown":
        sql += "\nGROUP BY lu_desc ORDER BY area_m2 DESC"
    elif q["op"] == "list":
        order = {"area_desc": "area_m2 DESC", "gpr_desc": "gpr_numeric DESC"}.get(q.get("sort"), "objectid")
        sql += f"\nORDER BY {order}"
        if "limit" in q:
            sql += f"\nLIMIT {q['limit']}"
    return sql
