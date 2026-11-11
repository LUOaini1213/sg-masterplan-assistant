"""Compute expected answers for eval/questions.jsonl WITHOUT the assistant's code.

Independent path: plain json + shapely on the committed GeoJSON. It does not import
sgmp, geopandas or pandas, so a bug in the engine cannot leak into the answer key.
Writes eval/expected.json (main set) and eval/heldout_expected.json (held-out set).
"""
import json
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "data" / "extract"
SETS = {"main": ("questions.jsonl", "expected.json"),
        "heldout": ("heldout_questions.jsonl", "heldout_expected.json")}


def features(name):
    return json.loads((EX / f"{name}.geojson").read_text(encoding="utf-8"))["features"]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def passes(p, g):
    if "planning_area" in g and p["PLN_AREA_N"] != g["planning_area"]:
        return False
    if "subzone" in g and p["SUBZONE_N"] != g["subzone"]:
        return False
    if "land_use" in g and p["LU_DESC"] not in g["land_use"]:
        return False
    if "gpr" in g:
        x, c, v = num(p["GPR"]), g["gpr"]["cmp"], g["gpr"]["value"]
        if x is None:
            return False
        ok = {">": x > v, ">=": x >= v, "<": x < v, "<=": x <= v, "=": abs(x - v) < 1e-9}[c]
        if not ok:
            return False
    return True


def answer(g, parcels, stations):
    rows = []
    buf = None
    if "near" in g:
        buf = stations[g["near"]["station"]].buffer(g["near"]["radius_m"])
    for p, geom in parcels:
        if not passes(p, g):
            continue
        if buf is not None:
            if not geom.intersects(buf):
                continue
            geom = geom.intersection(buf)
        rows.append((p, geom.area))
    op = g["op"]
    if op == "count":
        return len(rows)
    if op == "total_area":
        return sum(a for _, a in rows)
    if op == "breakdown":
        out = {}
        for p, a in rows:
            out[p["LU_DESC"]] = out.get(p["LU_DESC"], 0.0) + a
        return out
    if g.get("sort") == "area_desc":
        rows.sort(key=lambda r: (-r[1], r[0]["OBJECTID"]))
    elif g.get("sort") == "gpr_desc":
        rows.sort(key=lambda r: (-(num(r[0]["GPR"]) if num(r[0]["GPR"]) is not None else -1e9),
                                 r[0]["OBJECTID"]))
    else:
        rows.sort(key=lambda r: r[0]["OBJECTID"])
    if "limit" in g:
        rows = rows[: g["limit"]]
    return [p["OBJECTID"] for p, _ in rows]


def main():
    parcels = [(f["properties"], shape(f["geometry"])) for f in features("landuse")]
    stations = {f["properties"]["STATION"]: Point(f["geometry"]["coordinates"])
                for f in features("mrt_stations")}
    for src, dst in SETS.values():
        out = {}
        for line in (ROOT / "eval" / src).read_text(encoding="utf-8").splitlines():
            q = json.loads(line)
            if q.get("refuse"):
                out[q["id"]] = {"refuse": True}
            else:
                out[q["id"]] = {"op": q["gold"]["op"], "answer": answer(q["gold"], parcels, stations)}
        (ROOT / "eval" / dst).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(f"{dst}: {len(out)} expected answers")


if __name__ == "__main__":
    main()
