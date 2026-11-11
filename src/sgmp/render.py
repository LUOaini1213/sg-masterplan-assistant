"""What the planner sees: map PNG, table CSV, and the query with units and data vintage."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .data import load  # noqa: E402
from .dsl import to_sql  # noqa: E402
from .vocab import COVERAGE, DATA_VINTAGE  # noqa: E402


def summary_line(res):
    q = res.query
    if q["op"] == "refuse":
        return f"Refused: {q['reason']}"
    if q["op"] == "count":
        return f"{res.value} parcels"
    if q["op"] == "total_area":
        return f"{res.value:,.0f} m2 ({res.value / 1e4:,.2f} ha) across {len(res.parcels)} parcels"
    if q["op"] == "breakdown":
        return f"{len(res.table)} land-use codes, {res.table['area_m2'].sum() / 1e4:,.2f} ha in total"
    return f"{res.value} parcels listed"


def query_text(question, res, parser_name):
    lines = [f"Question: {question}", f"Read by: {parser_name}", "",
             "Query (allow-listed, read-only):", json.dumps(res.query, indent=2), "",
             "Equivalent SQL:", to_sql(res.query), "",
             f"Answer: {summary_line(res)}",
             "Units: area in square metres (m2) and hectares (ha), computed in SVY21 (EPSG:3414).",
             "GPR = gross plot ratio as zoned; LND/EVA/SDP/NA codes are not numeric.",
             "Near-station queries: a parcel counts if it touches the buffer; its area is "
             "only the part inside the buffer.",
             f"Data: {DATA_VINTAGE}. Coverage: {', '.join(COVERAGE)} only.",
             "Parcels are assigned to a planning area/subzone by their representative point."]
    lines += [f"Warning: {w}" for w in res.warnings]
    return "\n".join(lines) + "\n"


def draw_map(res, path, title):
    d = load()
    fig, ax = plt.subplots(figsize=(7, 7), dpi=110)
    d["planning_areas"].boundary.plot(ax=ax, color="#555555", linewidth=0.8)
    bg = d["landuse"]
    if res.buffer is not None:
        bg = bg[bg.intersects(res.buffer.buffer(300))]
    elif "planning_area" in res.query:
        bg = bg[bg.PLN_AREA_N == res.query["planning_area"]]
    elif "subzone" in res.query:
        bg = bg[bg.SUBZONE_N == res.query["subzone"]]
    bg.plot(ax=ax, color="#e6e6e6", edgecolor="#ffffff", linewidth=0.2)
    sel = res.parcels
    if sel is not None and len(sel):
        sel.plot(ax=ax, column="LU_DESC", categorical=True, legend=True, cmap="tab20",
                 edgecolor="#333333", linewidth=0.3,
                 legend_kwds={"loc": "upper left", "bbox_to_anchor": (1.0, 1.0), "fontsize": 7})
    if res.buffer is not None:
        ax.plot(*res.buffer.exterior.xy, color="#c0392b", linewidth=1.2)
        c = res.buffer.centroid
        ax.plot(c.x, c.y, marker="*", color="#c0392b", markersize=12)
        ax.annotate(f"{res.query['near']['station']} MRT", (c.x, c.y), xytext=(6, 6),
                    textcoords="offset points", fontsize=8, color="#c0392b")
    xmin, ymin, xmax, ymax = (res.buffer.bounds if res.buffer is not None else bg.total_bounds)
    pad = 0.05 * max(xmax - xmin, ymax - ymin, 100)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("SVY21 easting (m)", fontsize=7)
    ax.set_ylabel("SVY21 northing (m)", fontsize=7)
    ax.tick_params(labelsize=6)
    fig.text(0.01, 0.01, "Master Plan 2025 data (c) URA, Singapore Open Data Licence. "
             "Not an official URA product.", fontsize=6)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def write_outputs(question, res, out_dir, parser_name):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "query.txt").write_text(query_text(question, res, parser_name), encoding="utf-8")
    if res.query["op"] == "refuse":
        return [out / "query.txt"]
    res.table.to_csv(out / "table.csv", index=False, float_format="%.1f")
    draw_map(res, out / "map.png", f"{question}\n{summary_line(res)}")
    return [out / "query.txt", out / "table.csv", out / "map.png"]
