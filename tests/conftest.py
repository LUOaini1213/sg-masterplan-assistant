import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(qfile, efile):
    items = [json.loads(x) for x in (ROOT / "eval" / qfile).read_text(encoding="utf-8").splitlines()]
    expected = json.loads((ROOT / "eval" / efile).read_text(encoding="utf-8"))
    return items, expected


@pytest.fixture(scope="session")
def main_set():
    return _load("questions.jsonl", "expected.json")


@pytest.fixture(scope="session")
def heldout_set():
    return _load("heldout_questions.jsonl", "heldout_expected.json")
