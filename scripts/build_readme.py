"""Generate README.md from docs/README.template.md and the JSON files in results/.

Placeholders:
  {{file.json:dotted.key}}        value as stored
  {{file.json:dotted.key|pct}}    fraction shown as a percentage with one decimal
  {{file.json:dotted.key|ha}}     square metres shown as hectares with two decimals
  {{failures:file.json}}          markdown table of the failure cases in that results file
  {{mutants:file.json}}           markdown table of the mutants in that results file

python scripts/build_readme.py           write README.md
python scripts/build_readme.py --check   exit 1 if README.md is stale
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "README.template.md"
PLACEHOLDER = re.compile(r"\{\{([^}]+)\}\}")


def _get(obj, dotted):
    for part in dotted.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def _results(name):
    return json.loads((ROOT / "results" / name).read_text(encoding="utf-8"))


def fmt(val, kind):
    if kind == "pct":
        val = val * 100
        return f"{val:.1f}%"
    if kind == "ha":
        return f"{val / 1e4:,.2f}"
    return str(val)


def _cell(s):
    return str(s).replace("|", "/").replace("\n", " ")


def failures_table(name):
    rows = _results(name)["failures"]
    if not rows:
        return "_No failures._"
    out = ["| id | question | outcome | what the parser produced |", "|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['id']} | {_cell(r['question'])} | {r['outcome']} | `{_cell(json.dumps(r['parsed']))}` |")
    return "\n".join(out)


def mutants_table(name):
    out = ["| id | planted bug | result |", "|---|---|---|"]
    for r in _results(name)["mutants"]:
        out.append(f"| {r['id']} | {_cell(r['description'])} | {r['status']} |")
    return "\n".join(out)


def render(template):
    def sub(m):
        spec = m.group(1).strip()
        if spec.startswith("failures:"):
            return failures_table(spec.split(":", 1)[1])
        if spec.startswith("mutants:"):
            return mutants_table(spec.split(":", 1)[1])
        path, _, kind = spec.partition("|")
        name, key = path.split(":", 1)
        return fmt(_get(_results(name), key), kind)
    return PLACEHOLDER.sub(sub, template)


def main():
    text = render(TEMPLATE.read_text(encoding="utf-8"))
    readme = ROOT / "README.md"
    if "--check" in sys.argv:
        if not readme.exists() or readme.read_text(encoding="utf-8") != text:
            print("README.md is stale: run python scripts/build_readme.py")
            return 1
        return 0
    readme.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
