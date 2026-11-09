"""The eval scorer, on a tiny fake corpus with fake saved model outputs. No model call."""

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("HARBOR_EVAL_DIR", str(tmp_path / "eval"))
    monkeypatch.setenv("HARBOR_EVAL_RUNS", str(tmp_path / "runs"))
    monkeypatch.setenv("HARBOR_EVAL_REPORT", str(tmp_path / "report.md"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_evals

    return importlib.reload(run_evals)


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


DOC = """# Test SOP

Illustrative sample.

Document ID: SRC-T-001

## Purpose

This procedure explains how advocates handle a test request.

## Steps

Confirm the referral is on the account before you open an intake.

Verbatim (Legal): This estimate is not a guarantee of payment.

## Revision history

Version 1 created the document.
"""


def test_scorer_counts_hits_misses_and_consistency(tmp_path, monkeypatch):
    ev = _load(tmp_path, monkeypatch)
    root = tmp_path / "eval"
    _write(root / "test_sop.md", DOC)
    _write(
        root / "keys" / "test_sop_key.csv",
        "expected_unit_id,span_text,is_unit,type,roles,audience,knowledge_base,verbatim,section,notes\n"
        "E-1,Confirm the referral is on the account before you open an intake.,yes,procedure,Pharmacy advocate,advocate,pharmacy,no,Steps,\n"
        "E-2,This estimate is not a guarantee of payment.,yes,verbatim,Pharmacy advocate;Insurance advocate,both,pharmacy,yes,Steps,\n"
        ",This procedure explains how advocates handle a test request.,no,,,,,,Purpose,\n"
        ",Version 1 created the document.,no,,,,,,Revision history,\n",
    )
    _write(
        root / "sets" / "dedup_pairs.csv",
        "pair_id,text_a,text_b,expected_label,kind,notes\n"
        "P1,Call back within 2 business days.,Call back within 2 days.,different,lookalike,\n",
    )
    _write(
        root / "sets" / "drift_cases.csv",
        "case_id,doc_id,old_text,new_text,expected_change,notes\n"
        "D1,SRC-T-001,Hours end at 5 p.m.,Hours end at 6 p.m.,material,\n",
    )
    items = ev.build_inputs()
    by_eval = {item["eval"]: item for item in items}
    good = {"units": [
        {"title": "Referral", "type": "procedure", "text": "Confirm the referral is on the account before you open an intake.", "source_span": "Confirm the referral is on the account before you open an intake.", "tags": [], "domain": "", "audience": "advocate"},
        {"title": "Disclaimer", "type": "verbatim", "text": "This estimate is not a guarantee of payment.", "source_span": "This estimate is not a guarantee of payment.", "tags": [], "domain": "", "audience": "both"},
    ]}
    sloppy = {"units": good["units"][:1] + [
        {"title": "Disclaimer", "type": "verbatim", "text": "This estimate isn't a guarantee of payment.", "source_span": "This estimate is not a guarantee of payment.", "tags": [], "domain": "", "audience": "both"},
        {"title": "Purpose", "type": "policy", "text": "This procedure explains how advocates handle a test request.", "source_span": "This procedure explains how advocates handle a test request.", "tags": [], "domain": "", "audience": "advocate"},
    ]}
    outputs = {
        "extraction": [good, good, sloppy],
        "duplicates": [{"relation": "distinct", "differing_phrases": [], "reason": "", "confidence": "high"}] * 2 + [{"relation": "near_duplicate", "differing_phrases": [], "reason": "", "confidence": "low"}],
        "drift": [{"change": "material", "summary": "", "proposed_text": "Hours end at 6 p.m."}] * 3,
    }
    for run in range(3):
        for name, item in by_eval.items():
            ev.write_fixture(item["task"], item["content"], outputs[name][run], name, directory=tmp_path / "runs" / f"run{run + 1}")
    results = ev.score()
    ext = results["extraction"]
    assert ext["units_found"]["items"] == 2 and ext["units_found"]["majority_correct"] == 2
    assert ext["verbatim_exact"]["majority_correct"] == 1 and ext["verbatim_exact"]["correct_every_run"] == 0
    assert ext["left_alone"]["items"] == 2 and ext["left_alone"]["majority_correct"] == 2
    assert any(m["kind"] == "extracted text that should be left alone" for m in ext["misses"])
    dup = results["duplicates"]
    assert dup["overall"]["majority_correct"] == 1 and dup["false_merges_across_runs"] == 1
    assert dup["overall"]["consistency"]["same_every_run"] == 0
    assert results["drift"]["overall"]["correct_every_run"] == 1
    assert results["drift"]["material_fix_matches_new_source"] == {"matches": 3, "total": 3}
    assert json.loads((root / "results.json").read_text())["runs"] == 3
    assert "Every miss" in (tmp_path / "report.md").read_text()


def test_wilson_interval():
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_evals

    low, high = run_evals.wilson(40, 50)
    assert 0.66 < low < 0.7 and 0.88 < high < 0.9
