import json
import re
import subprocess

import yaml

from conftest import ROOT
from sgmp.data import load
from sgmp.vocab import LAND_USE_CODES, MANIFEST


def test_extract_matches_manifest_and_source_areas():
    d = load()
    lu = d["landuse"]
    assert len(lu) == MANIFEST["counts"]["landuse"]
    assert set(lu.PLN_AREA_N) == set(MANIFEST["planning_areas_in_extract"])
    assert set(lu.LU_DESC) <= set(LAND_USE_CODES)
    assert lu.OBJECTID.is_unique
    rel = ((lu.geometry.area - lu.SHAPE_AREA).abs() / lu.SHAPE_AREA)
    assert rel.median() < 1e-3  # our SVY21 area agrees with URA's SHAPE.AREA
    assert str(lu.crs).endswith("3414")


def _tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    if not out:  # not a git checkout: scan the tree
        out = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()
               and ".venv" not in p.parts and ".git" not in p.parts]
    return [ROOT / f for f in out if not f.endswith((".png", ".geojson"))]


def test_no_absolute_local_paths_committed():
    pat = re.compile(r"([A-Za-z]:[\\/]+Users[\\/])|(/home/[a-z])|(/Users/[A-Za-z])")
    bad = [str(p.relative_to(ROOT)) for p in _tracked_text_files()
           if p.exists() and pat.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert bad == []


def test_ci_yaml_parses_and_runs_pytest_offline():
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = ci["jobs"]["test"]["steps"]
    runs = " ".join(s.get("run", "") for s in steps)
    assert "pytest" in runs and "ollama" not in runs.lower()


def test_licence_is_mit():
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_eval_set_sizes():
    q = (ROOT / "eval/questions.jsonl").read_text(encoding="utf-8").splitlines()
    items = [json.loads(x) for x in q]
    assert sum(not i.get("refuse") for i in items) >= 30
    assert sum(bool(i.get("refuse")) for i in items) >= 10
