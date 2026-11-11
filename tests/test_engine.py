import hashlib

import pytest

from sgmp.data import gpr_number, load
from sgmp.engine import execute
from sgmp.scoring import result_matches


def _gold_items(items):
    return [it for it in items if not it.get("refuse")]


def test_engine_matches_independent_answer_key_main(main_set):
    items, expected = main_set
    bad = [it["id"] for it in _gold_items(items) if not result_matches(execute(it["gold"]), expected[it["id"]])]
    assert bad == []


def test_engine_matches_independent_answer_key_heldout(heldout_set):
    items, expected = heldout_set
    bad = [it["id"] for it in _gold_items(items) if not result_matches(execute(it["gold"]), expected[it["id"]])]
    assert bad == []


def _digest():
    lu = load()["landuse"]
    return hashlib.sha256(lu.to_wkb().to_csv().encode()).hexdigest()


def test_engine_is_read_only():
    before = _digest()
    execute({"op": "list", "near": {"station": "BISHAN", "radius_m": 800}, "sort": "area_desc"})
    execute({"op": "breakdown", "planning_area": "DOWNTOWN CORE"})
    assert _digest() == before


def test_near_area_is_clipped_to_buffer():
    r = execute({"op": "total_area", "near": {"station": "BISHAN", "radius_m": 300}})
    assert 0 < r.value <= r.buffer.area + 1e-6
    assert r.value > 0.5 * r.buffer.area  # Bishan MRT is inside the extract


def test_buffer_outside_extract_warns():
    assert execute({"op": "count", "near": {"station": "BISHAN", "radius_m": 300}}).warnings == []
    w = execute({"op": "count", "near": {"station": "BUGIS", "radius_m": 800}}).warnings
    assert len(w) == 1 and "outside" in w[0]
    # a small overhang (a few percent) must still be reported
    w = execute({"op": "count", "near": {"station": "UPPER THOMSON", "radius_m": 400}}).warnings
    assert len(w) == 1 and w[0].startswith("3%")


def test_count_list_total_consistent():
    base = {"planning_area": "DOWNTOWN CORE", "land_use": ["WHITE"]}
    n = execute({"op": "count", **base}).value
    lst = execute({"op": "list", **base})
    tot = execute({"op": "total_area", **base})
    assert n == len(lst.table) == tot.table["parcels"][0] > 0
    assert tot.value == pytest.approx(lst.table["AREA_M2"].sum())
    bd = execute({"op": "breakdown", **base})
    assert sum(bd.value.values()) == pytest.approx(tot.value)


def test_gpr_filters_exclude_non_numeric_and_respect_comparator():
    for cmp, ok in [(">", lambda g: g > 2.8), (">=", lambda g: g >= 2.8), ("<", lambda g: g < 2.8),
                    ("<=", lambda g: g <= 2.8), ("=", lambda g: g == 2.8)]:
        t = execute({"op": "list", "planning_area": "BISHAN", "gpr": {"cmp": cmp, "value": 2.8}}).table
        assert len(t) > 0
        assert all(ok(gpr_number(g)) for g in t["GPR"]), cmp


def test_sort_and_limit():
    t = execute({"op": "list", "planning_area": "BISHAN", "sort": "area_desc", "limit": 7}).table
    assert len(t) == 7 and list(t["AREA_M2"]) == sorted(t["AREA_M2"], reverse=True)
    g = execute({"op": "list", "planning_area": "BISHAN", "sort": "gpr_desc", "limit": 5}).table
    vals = [gpr_number(x) for x in g["GPR"]]
    assert vals == sorted(vals, reverse=True)


def test_gpr_number():
    assert gpr_number("2.8") == 2.8
    assert gpr_number("LND") is None and gpr_number(None) is None
