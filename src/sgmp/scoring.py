"""Execution-accuracy scoring: compare what a parsed query returns with the answer key."""
from .engine import execute

AREA_RTOL = 1e-3  # 0.1 % relative tolerance on areas


def close(a, b, rtol=AREA_RTOL):
    return abs(a - b) <= rtol * max(abs(b), 1.0)


def result_matches(result, expected):
    """expected: {"op", "answer"} from eval/expected.json."""
    exp = expected["answer"]
    if result.query["op"] != expected["op"]:
        return False
    if expected["op"] == "list":
        return [int(x) for x in result.table["OBJECTID"]] == list(exp)
    if expected["op"] == "count":
        return int(result.value) == int(exp)
    if expected["op"] == "total_area":
        return close(float(result.value), float(exp))
    if expected["op"] == "breakdown":
        got = result.value
        return set(got) == set(exp) and all(close(got[k], exp[k]) for k in exp)
    return False


def score_item(item, expected, parsed):
    """Return (outcome, detail). outcome in {"correct", "wrong", "refused", "false_refusal", "missed_refusal"}."""
    if item.get("refuse"):
        return ("refused", "") if parsed["op"] == "refuse" else ("missed_refusal", "query was run")
    if parsed["op"] == "refuse":
        return "false_refusal", parsed.get("reason", "")
    try:
        r = execute(parsed)
    except Exception as e:  # validated already; any error is a wrong answer
        return "wrong", f"execution error: {e}"
    return ("correct", "") if result_matches(r, expected) else ("wrong", "result differs from answer key")


def summarise(outcomes):
    ans = [o for o in outcomes if not o["refuse"]]
    ref = [o for o in outcomes if o["refuse"]]
    n_ok = sum(o["outcome"] == "correct" for o in ans)
    n_ref = sum(o["outcome"] == "refused" for o in ref)
    return {
        "n_answerable": len(ans),
        "n_correct": n_ok,
        "execution_accuracy": round(n_ok / len(ans), 4) if ans else 0.0,
        "n_false_refusals": sum(o["outcome"] == "false_refusal" for o in ans),
        "n_refusal_items": len(ref),
        "n_refused": n_ref,
        "refusal_rate": round(n_ref / len(ref), 4) if ref else 0.0,
        "failures": [o for o in outcomes if o["outcome"] not in ("correct", "refused")],
    }
