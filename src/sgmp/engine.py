"""Execute a validated query on the in-memory extract. Read-only: inputs are never modified."""
from dataclasses import dataclass, field

import pandas as pd

from .data import load
from .dsl import validate

CMP = {
    ">": lambda s, v: s > v,
    ">=": lambda s, v: s >= v,
    "<": lambda s, v: s < v,
    "<=": lambda s, v: s <= v,
    "=": lambda s, v: (s - v).abs() < 1e-9,
}


@dataclass
class Result:
    query: dict
    parcels: object = None  # GeoDataFrame of matched parcels (clipped to buffer if near)
    table: pd.DataFrame = None
    value: object = None  # count (int), area m2 (float), or None
    buffer: object = None
    warnings: list = field(default_factory=list)


def execute(q):
    q = validate(q)
    if q["op"] == "refuse":
        return Result(query=q)
    d = load()
    lu = d["landuse"]
    m = pd.Series(True, index=lu.index)
    if "planning_area" in q:
        m &= lu["PLN_AREA_N"] == q["planning_area"]
    if "subzone" in q:
        m &= lu["SUBZONE_N"] == q["subzone"]
    if "land_use" in q:
        m &= lu["LU_DESC"].isin(q["land_use"])
    if "gpr" in q:
        g = lu["GPR_NUM"].astype(float)
        m &= g.notna() & CMP[q["gpr"]["cmp"]](g, q["gpr"]["value"])
    sel = lu[m].copy()
    buf = None
    warnings = []
    if "near" in q:
        st = d["stations"]
        pt = st.loc[st.STATION == q["near"]["station"]].geometry.iloc[0]
        buf = pt.buffer(q["near"]["radius_m"])
        sel = sel[sel.intersects(buf)].copy()
        sel["geometry"] = sel.geometry.intersection(buf)
        sel["AREA_M2"] = sel.geometry.area
        covered = d["planning_areas"].geometry.union_all()
        outside = buf.difference(covered).area / buf.area
        if outside > 0.001:
            warnings.append(f"{outside:.0%} of the {q['near']['radius_m']:g} m buffer lies outside "
                            "the planning areas in this extract; land there is not counted.")
    cols = ["OBJECTID", "LU_DESC", "GPR", "PLN_AREA_N", "SUBZONE_N", "AREA_M2"]
    res = Result(query=q, buffer=buf, warnings=warnings)
    if q["op"] == "list":
        if q.get("sort") == "area_desc":
            sel = sel.sort_values(["AREA_M2", "OBJECTID"], ascending=[False, True])
        elif q.get("sort") == "gpr_desc":
            sel = sel.sort_values(["GPR_NUM", "OBJECTID"], ascending=[False, True], na_position="last")
        else:
            sel = sel.sort_values("OBJECTID")
        if "limit" in q:
            sel = sel.head(q["limit"])
        res.table = sel[cols].reset_index(drop=True)
        res.value = len(sel)
    elif q["op"] == "count":
        res.value = int(len(sel))
        res.table = pd.DataFrame({"parcels": [res.value]})
    elif q["op"] == "total_area":
        res.value = float(sel["AREA_M2"].sum())
        res.table = pd.DataFrame({"parcels": [len(sel)], "area_m2": [res.value],
                                  "area_ha": [res.value / 1e4]})
    elif q["op"] == "breakdown":
        t = (sel.groupby("LU_DESC").agg(parcels=("OBJECTID", "size"), area_m2=("AREA_M2", "sum"))
             .reset_index().sort_values(["area_m2", "LU_DESC"], ascending=[False, True]))
        t["area_ha"] = t["area_m2"] / 1e4
        res.table = t.reset_index(drop=True)
        res.value = {r.LU_DESC: float(r.area_m2) for r in t.itertuples()}
    res.parcels = sel
    return res
