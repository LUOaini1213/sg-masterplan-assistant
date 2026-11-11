"""Run the eval set through a parser and write results/eval_<name>.json.

python eval/run_eval.py rules
python eval/run_eval.py llm --model qwen3.5:4b      (needs a local Ollama server)
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from sgmp import parser_rules  # noqa: E402
from sgmp.scoring import AREA_RTOL, score_item, summarise  # noqa: E402
from compute_expected import SETS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parser", choices=["rules", "llm"])
    ap.add_argument("--model", default="qwen3.5:4b")
    ap.add_argument("--set", choices=["main", "heldout"], default="main")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    qfile, efile = SETS[a.set]
    items = [json.loads(x) for x in (ROOT / "eval" / qfile).read_text(encoding="utf-8").splitlines()]
    expected = json.loads((ROOT / "eval" / efile).read_text(encoding="utf-8"))
    outcomes, secs = [], []
    for it in items:
        t0 = time.perf_counter()
        if a.parser == "rules":
            parsed, raw = parser_rules.parse(it["question"]), None
        else:
            from sgmp import parser_llm
            parsed, raw = parser_llm.parse(it["question"], model=a.model)
        secs.append(time.perf_counter() - t0)
        outcome, detail = score_item(it, expected[it["id"]], parsed)
        o = {"id": it["id"], "question": it["question"], "refuse": bool(it.get("refuse")),
             "outcome": outcome, "detail": detail, "parsed": parsed}
        if not it.get("refuse"):
            o["gold"] = it["gold"]
        if raw is not None and outcome not in ("correct", "refused"):
            o["raw_model_output"] = raw
        outcomes.append(o)
        print(it["id"], outcome, detail, flush=True)
    s = summarise(outcomes)
    s["parser"] = a.parser if a.parser == "rules" else f"llm:{a.model}"
    s["question_set"] = a.set
    s["area_rtol"] = AREA_RTOL
    s["median_seconds_per_question"] = round(sorted(secs)[len(secs) // 2], 3)
    s["outcomes"] = outcomes
    name = a.out or ("eval_" + a.set + "_" + ("rules" if a.parser == "rules" else "llm"))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / f"{name}.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k not in ("failures", "outcomes")}))


if __name__ == "__main__":
    main()
