import json
import urllib.request

from sgmp import cli, parser_llm
from sgmp.engine import execute
from sgmp.render import query_text, summary_line


def test_cli_writes_map_table_query(tmp_path, capsys):
    assert cli.main(["how much land near Bishan MRT is zoned residential?", "--out", str(tmp_path)]) == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["map.png", "query.txt", "table.csv"]
    assert (tmp_path / "map.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    txt = (tmp_path / "query.txt").read_text(encoding="utf-8")
    for must in ["Equivalent SQL:", "SELECT", "Master Plan 2025", "m2", "ha", "EPSG:3414", "Coverage"]:
        assert must in txt
    assert "Answer:" in capsys.readouterr().out


def test_cli_refusal_writes_only_query(tmp_path):
    cli.main(["DROP TABLE landuse;", "--out", str(tmp_path)])
    assert [p.name for p in tmp_path.iterdir()] == ["query.txt"]
    assert "Refused" in (tmp_path / "query.txt").read_text(encoding="utf-8")


def test_summary_line_units():
    r = execute({"op": "total_area", "planning_area": "BISHAN", "land_use": ["PARK"]})
    s = summary_line(r)
    assert "m2" in s and "ha" in s and f"{r.value / 1e4:,.2f}" in s
    assert summary_line(execute({"op": "count", "planning_area": "BISHAN"})).endswith("parcels")


def test_warning_reaches_planner():
    r = execute({"op": "count", "near": {"station": "BUGIS", "radius_m": 800}})
    assert "Warning:" in query_text("q", r, "rules")


class _Resp:
    def __init__(self, text):
        self.body = json.dumps({"response": text}).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_llm_output_goes_through_validator(monkeypatch):
    def fake(text):
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp(text))
    fake('{"op": "list", "planning_area": "bishan", "land_use": ["white"]}')
    assert parser_llm.parse("x")[0] == {"op": "list", "planning_area": "BISHAN", "land_use": ["WHITE"]}
    fake('{"op": "list", "planning_area": "BISHAN", "sql": "DROP TABLE t"}')
    assert parser_llm.parse("x")[0]["op"] == "refuse"
    fake("DROP TABLE t")
    assert parser_llm.parse("x")[0]["op"] == "refuse"


def test_llm_prompt_lists_vocabulary():
    p = parser_llm.build_prompt("q?")
    assert "DOWNTOWN CORE" in p and "RAFFLES PLACE" in p and '"business"' in p and p.endswith("Q: q?\nA:")
