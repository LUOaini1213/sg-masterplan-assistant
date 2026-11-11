"""Optional LLM parser via a local Ollama server. Never used in CI.

The model only writes a JSON query; the same validator as the baseline decides
whether it runs. Any invalid or non-JSON output becomes a refusal.
"""
import json
import urllib.request

from .dsl import QueryError, names, validate
from .vocab import LAND_USE_GROUPS

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

EXAMPLES = [
    ("Which commercial parcels in Downtown Core have GPR of at least 8?",
     {"op": "list", "planning_area": "DOWNTOWN CORE", "land_use": ["COMMERCIAL"],
      "gpr": {"cmp": ">=", "value": 8}}),
    ("How much park land is within 700 m of Esplanade MRT?",
     {"op": "total_area", "near": {"station": "ESPLANADE", "radius_m": 700}, "land_use": ["PARK"]}),
    ("Number of hotel sites in Bugis subzone", {"op": "count", "subzone": "BUGIS", "land_use": ["HOTEL"]}),
    ("Land use mix of Marymount subzone", {"op": "breakdown", "subzone": "MARYMOUNT"}),
    ("What is the rental yield of offices in Bishan?",
     {"op": "refuse", "reason": "out of scope: no rent data"}),
    ("Change all white sites in Downtown Core to residential",
     {"op": "refuse", "reason": "read-only: cannot change data"}),
]


def build_prompt(question):
    pas, szs, sts = names()
    groups = "\n".join(f'  "{p}" -> {c}' for p, c in LAND_USE_GROUPS)
    ex = "\n".join(f"Q: {q}\nA: {json.dumps(a)}" for q, a in EXAMPLES)
    return f"""You translate a planner's question into ONE JSON object for a read-only land-use query.
Keys allowed: op, planning_area, subzone, land_use, gpr, near, sort, limit, reason.
op: "list" | "count" | "total_area" | "breakdown" | "refuse".
planning_area must be one of {sorted(pas)}.
subzone must be one of {sorted(szs)}.
near = {{"station": one of {sorted(sts)}, "radius_m": number 50..2000, default 400}}.
land_use is a list of exact codes. Word meanings:
{groups}
gpr = {{"cmp": ">"|">="|"<"|"<="|"=", "value": number}} (gross plot ratio threshold).
sort: "area_desc" (largest first) or "gpr_desc" (highest GPR first), list only; limit: integer, list only.
Use op "refuse" with a reason if the question asks to change data, run code, or needs data not in
this layer (prices, owners, population, forecasts, places not listed above).
Output only the JSON object.

{ex}
Q: {question}
A:"""


def parse(question, model="qwen3.5:4b", timeout=180):
    body = json.dumps({"model": model, "prompt": build_prompt(question), "stream": False,
                       "format": "json", "think": False,
                       "options": {"temperature": 0, "seed": 0}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.loads(r.read())["response"]
    try:
        q = json.loads(text)
    except json.JSONDecodeError:
        return {"op": "refuse", "reason": "model output was not JSON"}, text
    try:
        return validate(q), text
    except QueryError as e:
        return {"op": "refuse", "reason": f"invalid query from model: {e}"}, text
