"""Plant one bug at a time in a throw-away copy of the repo and check the tests catch it.

python mutation/run_mutation.py [--out results/mutation.json]

A mutant is "killed" if pytest fails with it in place. Each mutant must apply to exactly
one location, so a typo in this list cannot silently test nothing.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY = ["src", "tests", "eval", "data", "scripts", "results", "docs", ".github",
        "pyproject.toml", "LICENSE", "README.md"]

MUTANTS = [
    # (id, file, original, mutated, what it simulates)
    ("M01", "src/sgmp/engine.py", '">": lambda s, v: s > v', '">": lambda s, v: s >= v', "GPR > becomes >="),
    ("M02", "src/sgmp/engine.py", '"<": lambda s, v: s < v', '"<": lambda s, v: s <= v', "GPR < becomes <="),
    # M03 is expected to survive: NaN comparisons are already False, so notna() is redundant
    # (an equivalent mutant). Kept so the report shows it rather than hiding it.
    ("M03", "src/sgmp/engine.py", "m &= g.notna() & ", "m &= ", "non-numeric GPR not excluded (equivalent mutant)"),
    ("M04", "src/sgmp/engine.py", 'sel["geometry"] = sel.geometry.intersection(buf)', "pass",
     "near-station area not clipped to buffer"),
    ("M05", "src/sgmp/engine.py", "sel = sel[sel.intersects(buf)].copy()", "sel = sel[sel.within(buf)].copy()",
     "touching parcels dropped"),
    ("M06", "src/sgmp/engine.py", 'm &= lu["SUBZONE_N"] == q["subzone"]', "pass", "subzone filter ignored"),
    ("M07", "src/sgmp/engine.py", 'ascending=[False, True])\n        elif', 'ascending=[True, True])\n        elif',
     "largest-first sort reversed"),
    ("M08", "src/sgmp/engine.py", "if outside > 0.001:", "if outside > 0.5:", "coverage warning suppressed"),
    ("M09", "src/sgmp/engine.py", 'res.value = float(sel["AREA_M2"].sum())', 'res.value = float(sel["AREA_M2"].mean())',
     "total area uses mean"),
    ("M10", "src/sgmp/dsl.py", "if not MIN_RADIUS <= r <= MAX_RADIUS:", "if not MIN_RADIUS <= r:",
     "radius upper bound dropped"),
    ("M11", "src/sgmp/dsl.py", "extra = set(q) - KEYS", "extra = set()", "unknown keys accepted"),
    ("M12", "src/sgmp/dsl.py", "        if bad:\n            raise QueryError(f\"unknown land-use", "        if False:\n            raise QueryError(f\"unknown land-use",
     "unknown land-use codes accepted"),
    ("M13", "src/sgmp/dsl.py", 'if not any(k in out for k in ("planning_area", "subzone", "near")):', "if False:",
     "spatial scope not required"),
    ("M14", "src/sgmp/dsl.py", "DEFAULT_RADIUS = 400", "DEFAULT_RADIUS = 500", "default walking radius changed"),
    ("M15", "src/sgmp/parser_rules.py", '("at least", ">="), ', "", "'at least' parsed as '='"),
    ("M16", "src/sgmp/parser_rules.py", '("above", ">"), ', '("above", ">="), ', "'above' parsed as >="),
    ("M17", "src/sgmp/parser_rules.py", '(1000 if m.group(2).startswith("k") else 1)', "1",
     "km not converted to metres"),
    ("M18", "src/sgmp/parser_rules.py", 'r"\\b(drop|delete|insert|update|alter|truncate|grant|exec|execute|attach|pragma)\\b",\n', "",
     "SQL verbs not refused"),
    ("M19", "src/sgmp/parser_rules.py", 'r"\\bprices?\\b", ', "", "price questions not refused"),
    ("M20", "src/sgmp/parser_rules.py", "        sz = bare  # e.g.", "        pass  # e.g.",
     "subzone named like its planning area misread"),
    ("M21", "src/sgmp/vocab.py", '("business", ["BUSINESS 1", "BUSINESS 2", "BUSINESS PARK"]),',
     '("business", ["BUSINESS 1", "BUSINESS 2"]),', "'business' drops business park"),
    ("M22", "src/sgmp/vocab.py", '("green", ["PARK", "OPEN SPACE"]),', '("green", ["PARK"]),',
     "'green' drops open space"),
    ("M23", "src/sgmp/scoring.py", "AREA_RTOL = 1e-3", "AREA_RTOL = 1e-1", "area tolerance too loose"),
    ("M24", "src/sgmp/scoring.py", 'return [int(x) for x in result.table["OBJECTID"]] == list(exp)',
     'return sorted(int(x) for x in result.table["OBJECTID"]) == sorted(exp)', "list order ignored"),
    ("M25", "src/sgmp/render.py", '"Equivalent SQL:", to_sql(res.query), "",', '"",',
     "query not shown to planner"),
    ("M26", "src/sgmp/render.py", 'f"Data: {DATA_VINTAGE}. Coverage', 'f"Coverage', "data vintage hidden"),
    ("M27", "src/sgmp/parser_llm.py", "        return validate(q), text", "        return q, text",
     "LLM output bypasses validator"),
    ("M28", "src/sgmp/data.py", "        return float(v)", "        return float(v) if v != 'EVA' else 0.0",
     "envelope-control parcels given GPR 0"),
    ("M29", "scripts/build_readme.py", "        val = val * 100", "        val = val", "percent not scaled"),
]


def run_one(base, mutant):
    mid, f, old, new, _ = mutant
    p = base / f
    src = p.read_text(encoding="utf-8")
    n = src.count(old)
    if n != 1:
        return {"id": mid, "status": "invalid", "detail": f"pattern found {n} times"}
    p.write_text(src.replace(old, new), encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"],
                           cwd=base, capture_output=True, text=True, timeout=900)
    finally:
        p.write_text(src, encoding="utf-8")
    killed = r.returncode != 0
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    return {"id": mid, "status": "killed" if killed else "survived", "detail": tail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/mutation.json")
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="sgmp_mut_"))
    try:
        for c in COPY:
            s = ROOT / c
            if s.is_dir():
                shutil.copytree(s, tmp / c, ignore=shutil.ignore_patterns("__pycache__"))
            elif s.exists():
                shutil.copy2(s, tmp / c)
        # The README embeds this script's own output, which does not exist yet on a first run.
        # In the throw-away copy only, stub it and regenerate the README so the suite is green.
        for name in ("mutation.json", "mutation_first_run.json"):
            if not (tmp / "results" / name).exists():
                (tmp / "results" / name).write_text(json.dumps(
                    {"n_mutants": 0, "n_killed": 0, "n_survived": 0, "n_invalid": 0, "mutants": []}),
                    encoding="utf-8")
        subprocess.run([sys.executable, "scripts/build_readme.py"], cwd=tmp, check=True)
        base = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                              cwd=tmp, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("unmutated copy fails its tests; fix that first\n" + base.stdout[-2000:])
        rows = []
        for m in MUTANTS:
            r = run_one(tmp, m)
            r["file"], r["description"] = m[1], m[4]
            rows.append(r)
            print(r["id"], r["status"], r["description"], flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = {"n_mutants": len(rows),
           "n_killed": sum(r["status"] == "killed" for r in rows),
           "n_survived": sum(r["status"] == "survived" for r in rows),
           "n_invalid": sum(r["status"] == "invalid" for r in rows),
           "mutants": rows}
    (ROOT / a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "mutants"}))


if __name__ == "__main__":
    main()
