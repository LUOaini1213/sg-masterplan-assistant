"""README numbers must come from results/: the README is a pure function of the template and
results/*.json, and the template's own prose may only contain a short list of fixed numbers."""
import re

from conftest import ROOT

import build_readme

# Numbers allowed to appear literally in the template (not results): dataset vintages,
# licence version, CRS code, fixed design parameters, and counts of UX tasks.
ALLOWED_STATIC = {"2019", "2025", "2026", "1.0", "3414", "400", "50", "2000", "3", "1", "2"}


def _static_text(template):
    t = re.sub(r"```.*?```", " ", template, flags=re.S)      # code blocks
    t = build_readme.PLACEHOLDER.sub(" ", t)                 # placeholders
    t = re.sub(r"`[^`]*`", " ", t)                           # inline code
    t = re.sub(r"\(?https?://\S+", " ", t)                    # URLs
    t = re.sub(r"\]\([^)]*\)", "]", t)                       # relative links
    t = re.sub(r"\bd_[0-9a-f]{32}\b", " ", t)                # dataset ids
    return t


def test_readme_is_generated_from_results():
    tpl = (ROOT / "docs/README.template.md").read_text(encoding="utf-8")
    assert (ROOT / "README.md").read_text(encoding="utf-8") == build_readme.render(tpl)


def test_template_has_no_hand_typed_numbers():
    tpl = (ROOT / "docs/README.template.md").read_text(encoding="utf-8")
    nums = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", _static_text(tpl)))
    assert nums <= ALLOWED_STATIC, sorted(nums - ALLOWED_STATIC)


def test_every_placeholder_resolves_to_a_results_file():
    tpl = (ROOT / "docs/README.template.md").read_text(encoding="utf-8")
    specs = build_readme.PLACEHOLDER.findall(tpl)
    assert specs
    for s in specs:
        name = s.split(":", 1)[1] if s.startswith(("failures:", "mutants:")) else s.split(":", 1)[0]
        assert (ROOT / "results" / name.split("|")[0]).exists(), s


def test_fmt():
    assert build_readme.fmt(0.7, "pct") == "70.0%"
    assert build_readme.fmt(25000.0, "ha") == "2.50"
    assert build_readme.fmt(12, "") == "12"
