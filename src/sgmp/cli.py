"""Ask a question: python -m sgmp.cli "which residential parcels in Bishan have GPR above 3?" --out out/

Writes out/query.txt (the query it ran), out/table.csv and out/map.png.
"""
import argparse
import sys

from . import parser_rules
from .engine import execute
from .render import query_text, write_outputs


def ask(question, use_llm=False, model="qwen3.5:4b"):
    if use_llm:
        from . import parser_llm
        q, _ = parser_llm.parse(question, model=model)
        name = f"local LLM ({model}) + validator"
    else:
        q = parser_rules.parse(question)
        name = "rule-based parser (deterministic)"
    return execute(q), name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--out", default="out")
    ap.add_argument("--llm", action="store_true", help="use a local Ollama model instead of rules")
    ap.add_argument("--model", default="qwen3.5:4b")
    a = ap.parse_args(argv)
    res, name = ask(a.question, a.llm, a.model)
    sys.stdout.write(query_text(a.question, res, name))
    if res.table is not None:
        sys.stdout.write("\n" + res.table.head(20).to_string(index=False) + "\n")
    for p in write_outputs(a.question, res, a.out, name):
        sys.stdout.write(f"wrote {p.as_posix()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
