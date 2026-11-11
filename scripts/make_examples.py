"""Run the example questions with the rule-based parser.

Writes docs/examples/<n>/{query.txt,table.csv,map.png} and results/examples.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sgmp.cli import ask  # noqa: E402
from sgmp.render import summary_line, write_outputs  # noqa: E402

QUESTIONS = [
    "which residential parcels in Bishan have GPR above 3?",
    "how much land near Bishan MRT is zoned business?",
    "what is the land use mix near Bishan MRT?",
    "list white sites in Downtown Core",
]


def main():
    out = []
    for i, q in enumerate(QUESTIONS, 1):
        res, name = ask(q)
        write_outputs(q, res, ROOT / "docs" / "examples" / str(i), name)
        row = {"question": q, "query": res.query, "answer": summary_line(res),
               "n_parcels": int(len(res.parcels)) if res.parcels is not None else 0}
        if res.query["op"] == "total_area":
            row["area_m2"] = round(res.value, 1)
        if res.query["op"] == "breakdown":
            row["top_land_use"] = res.table.iloc[0]["LU_DESC"]
            row["top_land_use_ha"] = round(float(res.table.iloc[0]["area_ha"]), 2)
            row["total_ha"] = round(float(res.table["area_ha"].sum()), 2)
        if res.query["op"] == "list" and len(res.table):
            row["total_area_m2"] = round(float(res.table["AREA_M2"].sum()), 1)
        out.append(row)
        print(q, "->", row["answer"])
    (ROOT / "results" / "examples.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
