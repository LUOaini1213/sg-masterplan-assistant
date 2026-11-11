from sgmp.engine import execute
from sgmp.scoring import close, result_matches, score_item, summarise

Q = {"op": "total_area", "planning_area": "DOWNTOWN CORE", "land_use": ["WHITE"]}


def test_close_tolerance():
    assert close(1000.0, 1000.9)
    assert not close(1000.0, 1001.1)
    assert close(0.0, 0.0)


def test_result_matches_each_op():
    r = execute(Q)
    assert result_matches(r, {"op": "total_area", "answer": r.value * 1.0005})
    assert not result_matches(r, {"op": "total_area", "answer": r.value * 1.01})
    assert not result_matches(r, {"op": "count", "answer": r.value})
    c = execute({**Q, "op": "count"})
    assert result_matches(c, {"op": "count", "answer": c.value})
    assert not result_matches(c, {"op": "count", "answer": c.value + 1})
    lst = execute({**Q, "op": "list"})
    ids = [int(x) for x in lst.table["OBJECTID"]]
    assert result_matches(lst, {"op": "list", "answer": ids})
    assert not result_matches(lst, {"op": "list", "answer": ids[:-1]})
    assert not result_matches(lst, {"op": "list", "answer": ids[::-1]})
    b = execute({"op": "breakdown", "planning_area": "BISHAN"})
    assert result_matches(b, {"op": "breakdown", "answer": dict(b.value)})
    worse = dict(b.value)
    worse.pop(next(iter(worse)))
    assert not result_matches(b, {"op": "breakdown", "answer": worse})


def test_score_item_outcomes():
    ref = {"id": "x", "refuse": True}
    assert score_item(ref, {"refuse": True}, {"op": "refuse", "reason": ""})[0] == "refused"
    assert score_item(ref, {"refuse": True}, Q)[0] == "missed_refusal"
    item = {"id": "y", "gold": Q}
    exp = {"op": "total_area", "answer": execute(Q).value}
    assert score_item(item, exp, {"op": "refuse", "reason": "r"})[0] == "false_refusal"
    assert score_item(item, exp, Q)[0] == "correct"
    assert score_item(item, exp, {**Q, "land_use": ["HOTEL"]})[0] == "wrong"


def test_summarise_counts():
    outs = [{"refuse": False, "outcome": "correct"}, {"refuse": False, "outcome": "wrong"},
            {"refuse": False, "outcome": "false_refusal"}, {"refuse": True, "outcome": "refused"},
            {"refuse": True, "outcome": "missed_refusal"}]
    s = summarise(outs)
    assert (s["n_answerable"], s["n_correct"], s["n_false_refusals"]) == (3, 1, 1)
    assert s["execution_accuracy"] == round(1 / 3, 4)
    assert (s["n_refusal_items"], s["n_refused"], s["refusal_rate"]) == (2, 1, 0.5)
    assert len(s["failures"]) == 3
