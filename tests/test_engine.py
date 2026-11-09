"""Demo-path checks. Cached mode must not call the model."""

import csv
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("ANTHROPIC_API_KEY", None)

import src.ai as ai
from src.ai import DEMO_QUERIES, judge_user, pricing_sentence, replay
from src.corpus import load_corpus
from src.engine import (
    CATALOG,
    act_on_gap,
    activity,
    anchor,
    apply_prepared_drift,
    apply_source_span,
    apply_website_merge,
    approve_units,
    build_database,
    confirm_tags,
    connect,
    document_body,
    drift_state,
    escalate_conflict,
    extract_units,
    flag,
    gaps,
    keep_canonical,
    live_approved,
    publish_revision,
    quality_report,
    resolve_conflict,
    search,
    send_drift_to_legal,
    set_live,
    synonym_entries,
)

ROOT = Path(__file__).resolve().parents[1]
COST = "what do I say before I quote a cost"
TILE_KEYS = [
    "hit_at_1",
    "correct_abstain",
    "over_abstain",
    "leaks",
    "dedup_precision",
    "dedup_recall",
]


def _require(condition, message) -> None:
    if not condition:
        raise SystemExit(message)


def _walk(conn) -> None:
    extract_units(conn, record=True)
    confirm_tags(conn)
    apply_website_merge(conn)
    keep_canonical(conn)
    escalate_conflict(conn)
    approve_units(conn)


def _questions():
    seen = set()
    ordered = []

    def add(question, role):
        key = (question, role)
        if key in seen:
            return
        seen.add(key)
        ordered.append(key)

    for question, role in DEMO_QUERIES:
        add(question, role)
    for row in csv.DictReader((ROOT / "data" / "golden_set.csv").open()):
        add(row["question"], row["role"])
    return ordered


def _search_all(conn, label: str) -> None:
    for question, role in _questions():
        found = search(conn, role, question, record=True)
        if found["ai_source"] == "missing":
            raise SystemExit(f"{label} missing cache for {role}: {question}")


def main() -> None:
    calls = {"n": 0}

    def counting_refuse(*_args, **_kwargs):
        calls["n"] += 1
        raise RuntimeError("model call refused")

    ai.call_model = counting_refuse
    _require(ai.resolve_api_key() == "", "cached mode still sees an API key")
    for retired in ("v1_units", "benefits_units", "conflict_unit", "gaps"):
        _require(retired not in CATALOG, f"catalog still has {retired}")
    _require(CATALOG["channels_revision"].get("member_find"), "channels revision does not edit member text")
    _require(CATALOG["drift_edit"].get("cosmetic", {}).get("find") == "supply at", "cosmetic drift edit missing")
    _require(all(item["origin"] == "seed" for item in synonym_entries()), "synonym seed label missing")

    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "demo.sqlite")
    build_database(path, mode="start")
    conn = connect(path)
    _walk(conn)
    corpus = load_corpus()
    if "judge_variant" in dir(__import__("src.engine", fromlist=["engine"])):
        raise SystemExit("judge_variant is still defined")
    recorded = ai.load_human_decisions()["member_texts"]
    moved = {
        "U-RX-EDU-002-04": "U-RX-EDU-001-05",
        "U-RX-EDU-002-10": "U-RX-EDU-001-12",
        "U-RX-EDU-002-11": "U-RX-EDU-001-13",
        "U-RX-EDU-002-13": "U-RX-EDU-001-16",
    }
    for old, new in moved.items():
        _require(old not in recorded, f"member text still on retired unit {old}")
        _require(new in recorded and recorded[new].get("moved_from") == old, f"member text not moved to {new}")
    for unit_id in ("U-BEN-COST-001-02", "U-BEN-COST-001-05"):
        _require(unit_id in recorded, f"member text missing for {unit_id}")
    for unit_id, spec in recorded.items():
        row = conn.execute(
            "SELECT member_text FROM units WHERE unit_id = ? AND version = 1",
            (unit_id,),
        ).fetchone()
        _require(row and row["member_text"] == spec["member_text"], f"member text not stored for {unit_id}")

    pricing = anchor(conn, "pricing")
    _require(pricing, "pricing anchor missing")
    _search_all(conn, "approved")
    cost = search(conn, "Pharmacy advocate", COST)
    _require(cost["ai_source"] == "cached", f"cost query source {cost['ai_source']}")
    _require(not cost["abstained"] and cost["unit"]["unit_id"] == pricing, "pharmacy cost query")
    benefits = anchor(conn, "benefits")
    medical = search(conn, "Insurance advocate", "What do I say before I quote a medical cost?")
    _require(medical["ai_source"] == "cached", "medical query was not cached")
    _require(not medical["abstained"] and medical["unit"]["unit_id"] == benefits, "medical cost query")
    specialty = search(conn, "Insurance advocate", "do specialty drugs stay at the specialty pharmacy")
    _require(specialty["ai_source"] != "missing", specialty["ai_source"])

    before = live_approved(conn, pricing)
    _require("plan records I can see today" in before["text"], "advocate wording missing the revision phrase")
    _require("plan information we have today" in (before["member_text"] or ""), "member wording missing the revision phrase")
    _require("on this page" not in (before["member_text"] or ""), "member wording names a page")
    _require("on this call" not in (before["member_text"] or ""), "member wording names a call")
    merge_history = ai.load_human_decisions()["merges"][0]["member_text"]
    _require("on this page" in merge_history, "website merge history dropped the page sentence")
    plan = next(item for item in ai.load_human_decisions()["conflicts"] if item.get("resolve_in_demo"))
    resolved = resolve_conflict(conn, plan["reason"])
    _require(resolved.startswith("Kept"), resolved)
    _require(flag(conn, "conflict_resolved"), "conflict flag missing")
    _search_all(conn, "resolved")
    publish_revision(conn)
    after = live_approved(conn, pricing)
    _require(after["version"] == before["version"] + 1, "revision did not publish a new version")
    _require("available on this call" in after["text"], "advocate text was not revised")
    _require("plan information available today" in after["member_text"], "member text was not revised")
    _require("on this page" not in after["member_text"], "revised member wording names a page")
    _require("on this call" not in after["member_text"], "revised member wording names a call")
    _require("31-day" not in after["text"], "revision changed the days supply")
    _require("available on this call" in document_body(conn, "SRC-RX-EDU-001"), "publish did not update the source script")
    _require("plan records I can see today" not in document_body(conn, "SRC-RX-EDU-001"), "source script kept the version 1 phrase")
    _require(
        any("source passage" in row["message"] for row in activity(conn, 6)),
        "source update was not logged",
    )
    superseded = conn.execute(
        "SELECT status, search_visible FROM units WHERE unit_id = ? AND version = ?",
        (pricing, before["version"]),
    ).fetchone()
    _require(superseded["status"] == "superseded" and superseded["search_visible"] == 0, "old version still live")
    _search_all(conn, "revised")
    revised_hit = search(conn, "Pharmacy advocate", COST)
    _require(revised_hit["unit"]["version"] == after["version"], "search did not return the revised version")
    _require(revised_hit["ai_source"] != "missing", "revised search missing")

    _require(act_on_gap(conn, "c5", "write", "  ") == "A reason is required.", "empty gap reason was accepted")
    _require(
        act_on_gap(conn, "c5", "write", "Authors should draft the turnaround unit. Illustrative.") == "",
        "write gap failed",
    )
    _require(
        act_on_gap(conn, "c6", "fix_process", "Open the plan record instead of asking chat. Illustrative.") == "",
        "process fix failed",
    )
    _require(
        act_on_gap(conn, "c7", "dismiss", "These guides do not publish an insulin cap. Illustrative.") == "",
        "dismiss failed",
    )
    by_gap = {row["id"]: row for row in gaps(conn)}
    _require(by_gap["c5"]["status"] == "in_review" and "turnaround" in by_gap["c5"]["reason"], "write reason missing")
    _require(by_gap["c6"]["status"] == "process_fix" and by_gap["c6"]["reason"], "process reason missing")
    _require(by_gap["c7"]["status"] == "dismissed" and "insulin" in by_gap["c7"]["reason"], "dismiss reason missing")
    logged = " ".join(row["message"] for row in activity(conn, 30))
    _require("Reason:" in logged, "gap reasons were not logged")

    _require("30-day supply" in document_body(conn, "SRC-RX-EDU-001"), "source lost the prepared phrase")
    _require(apply_prepared_drift(conn, "cosmetic") == "", "cosmetic drift failed")
    cosmetic = drift_state(conn)
    _require(cosmetic["cosmetic"] and not cosmetic["material"], "cosmetic edit was flagged")
    _require(cosmetic["cosmetic_line"] == "Cosmetic change. Logged, not flagged.", cosmetic["cosmetic_line"])
    _require(not cosmetic["stale"], "cosmetic edit marked the unit stale")
    _require(cosmetic["events"] and cosmetic["events"][0]["flagged"] == 0, "cosmetic event flagged")
    _require(cosmetic["events"][0]["ai_source"] == "cached", "cosmetic source")
    _require("supply, at" in document_body(conn, "SRC-RX-EDU-001"), "cosmetic edit did not change the source")
    _require("31-day" not in cosmetic["live_text"], "cosmetic edit changed the live wording")

    _require(apply_prepared_drift(conn, "material") == "", "material drift failed")
    material = drift_state(conn)
    _require(material["material"] and material["stale"], "material edit was not flagged")
    _require("Waiting for Legal" in material["material_line"], material["material_line"])
    _require("31-day" not in material["live_text"], "material edit replaced the live wording")
    _require("31-day" in material["proposed_text"], "T5 proposal missing")
    _require("available on this call" in material["proposed_text"], "drift proposal dropped the published phrase")
    _require("I can see today" not in material["proposed_text"], "drift proposal restored the version 1 phrase")
    _require(material["events"][-1]["flagged"] == 1, "material event not flagged")
    _require(material["events"][-1]["ai_source"] == "cached", "material source")
    _require(material["events"][-1]["status"] == "awaiting_legal", material["events"][-1]["status"])
    live = live_approved(conn, pricing)
    _require(live["search_visible"] == 1 and "31-day" not in live["text"], "approved wording changed")
    still = search(conn, "Pharmacy advocate", COST)
    _require(still["unit"]["text"] == live["text"] and still["ai_source"] != "missing", "search left the approved wording")
    _require(send_drift_to_legal(conn) == "", "send to Legal failed")
    _require(drift_state(conn)["sent"], "drift was not marked sent")
    _require(live_approved(conn, pricing)["text"] == live["text"], "sending to Legal published the proposal")
    missing_edit = apply_source_span(conn, "This sentence is not a prepared edit.")
    _require("No cached result" in missing_edit, missing_edit)

    report = quality_report(conn)
    _require([tile["key"] for tile in report["tiles"]] == TILE_KEYS, "tile set")
    _require(all(tile["note"] == "Illustrative, made-up data" for tile in report["tiles"]), "tiles need an illustrative label")
    _require(report["golden_table"]["columns"] == ["Question", "Role", "Expected", "Got", "Result"], "golden columns")
    _require(len(report["golden_table"]["rows"]) == 12, f"scored rows {len(report['golden_table']['rows'])}")
    _require(len(report["golden_table"]["held_out"]) == 3, f"held-out rows {len(report['golden_table']['held_out'])}")
    _require(all(row["heldout"] == "yes" for row in report["golden_table"]["held_out"]), "held-out flag")
    _require(len(report["dedup_table"]["rows"]) == 20, f"dedup rows {len(report['dedup_table']['rows'])}")
    _require(
        all(row["reason"] and "No cached result" not in row["reason"] for row in report["dedup_table"]["rows"]),
        "dedup row missing the model reason",
    )
    _require(report["verbatim_source"]["label"] == "Verbatim units matching source", "verbatim label")
    _require(" of " in report["verbatim_source"]["display"], report["verbatim_source"]["display"])
    _require(report["note"] == "Illustrative, made-up data", "report label")
    for row in report["golden_table"]["rows"] + report["golden_table"]["held_out"]:
        if row["Result"] == "No saved answer" or row["ai_source"] == "missing":
            raise SystemExit(f"quality not cached for {row['Role']}: {row['Question']}")
    for item in report["misses"]:
        _require(item["next_step"] and "\n" not in item["next_step"], "miss needs a one-line next step")

    short_path = str(Path(folder) / "short.sqlite")
    build_database(short_path, mode="short")
    short = connect(short_path)
    for key in ("extracted", "canonical", "escalated"):
        _require(flag(short, key), f"short demo missing {key}")
    _require(not flag(short, "approved"), "short demo must not mark the queue finished")
    early = search(short, "Pharmacy advocate", COST)
    _require(early["ai_source"] != "missing", early["ai_source"])
    carried = short.execute(
        "SELECT member_text FROM units WHERE unit_id = 'U-BEN-COST-001-02' AND version = 1"
    ).fetchone()
    _require(carried and carried["member_text"], "short demo dropped member text")

    _require(calls["n"] == 0, f"cached mode called the model {calls['n']} times")
    sentence = pricing_sentence((ROOT / "data" / "rx_education_script.md").read_text())
    first = next(csv.DictReader((ROOT / "data" / "dedup_variants.csv").open()))
    user = judge_user("Canonical pricing disclaimer", sentence, "Variant", first["variant_text"])
    cached_output, cached_source = replay("judge_pair", user, live=False)
    _require(cached_source == "cached" and cached_output, cached_source)
    saved_output, saved_source = replay("judge_pair", user, live=True)
    _require(saved_source == "cached" and saved_output == cached_output, saved_source)
    _require(calls["n"] == 0, "a saved answer called the model")

    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
    set_live(conn, True)
    live_hit = search(conn, "Pharmacy advocate", COST, record=False)
    _require(live_hit["ai_source"] == "cached", live_hit["ai_source"])
    _require(live_hit["unit"]["unit_id"] == pricing, "saved answer was not used")
    _require(calls["n"] == 0, f"saved answer called the model {calls['n']} times")
    os.environ.pop("ANTHROPIC_API_KEY", None)
    set_live(conn, False)
    again = search(conn, "Pharmacy advocate", COST, record=False)
    _require(again["ai_source"] == "cached", again["ai_source"])
    _require(calls["n"] == 0, "cached mode called the model after live was turned off")

    print("units", len(corpus["units"]), "pool", len(corpus["pool"]), "pairs", len(corpus["judgments"]))
    print(
        "tiles",
        ", ".join(f"{tile['label']} {tile['display']} ({tile['detail']})" for tile in report["tiles"]),
    )
    print("verbatim", report["verbatim_source"]["display"])
    print("dedup rows", len(report["dedup_table"]["rows"]), "held-out", len(report["golden_table"]["held_out"]))
    print("misses", len(report["misses"]))
    for item in report["misses"]:
        print("-", item["miss"])
        print("  next:", item["next_step"])
    print("ok")


if __name__ == "__main__":
    main()
