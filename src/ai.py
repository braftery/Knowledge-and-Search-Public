"""Model calls and cached replay for the five knowledge tasks.

The generator in scripts/generate_fixtures.py is the only writer of fixtures/ai/.
Replay reads those files. Nothing in this module edits a saved model output.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "ai"
MODEL = "claude-opus-5-5"
BETA = "server-side-fallback-2026-07-01"

EXTRACT_PROMPT = (
    "You convert one contact center source document into candidate knowledge units "
    "for human review. A unit is the smallest statement an approver can approve on "
    "its own. For each unit return: a short title; a type (verbatim, policy, "
    "procedure, faq); the unit text; the exact source span copied character for "
    "character from the document; suggested tags; a domain; and an audience "
    "(advocate, member, or both). Lines marked \"Verbatim (Legal)\" are type "
    "verbatim, and their text must equal the source span exactly. Advocate notes "
    "and coaching are guidance: return them with type procedure, and never merge "
    "them into a verbatim unit. If a paragraph mixes a procedure with a policy, "
    "split it into separate units. Do not invent content that is not in the "
    "document. Return only the JSON."
)

JUDGE_PROMPT = (
    "You compare two knowledge statements from a health plan contact center. "
    "Decide their relationship: exact (same words, ignoring whitespace and "
    "punctuation), near_duplicate (same meaning and obligations, different "
    "wording), conflict (they address the same situation but give instructions "
    "or facts that cannot both be true), or distinct (different subjects). For "
    "near_duplicate and conflict, list the specific phrases that differ and "
    "explain in one sentence why. Treat any change to an amount, days' supply, "
    "pharmacy type, guarantee, eligibility condition, or who the statement "
    "applies to as a change in meaning. Return only the JSON."
)

SUFFICIENCY_PROMPT = (
    "You decide whether an approved knowledge unit answers an advocate's "
    "question. You see the question and up to three approved units the advocate "
    "is allowed to read. Choose the unit that fully answers the question, or "
    "choose none if no unit answers it. Do not combine units, and do not answer "
    "from your own knowledge. Return only the JSON."
)

GAP_PROMPT = (
    "Advocates searched for the questions below and no approved knowledge unit "
    "answered them. Draft a proposed knowledge unit an author can complete. "
    "Write it as the answer an advocate would give, with a placeholder in square "
    "brackets for every fact the documents do not provide, for example "
    "[number of days]. List what the author must confirm before approval. Do not "
    "invent facts. Return only the JSON."
)

DRIFT_PROMPT = (
    "A source document changed under an approved knowledge unit. Compare the old "
    "source span with the new one. Decide whether the change is material (it "
    "changes meaning, an amount, a condition, or required wording) or cosmetic "
    "(spacing, punctuation, typo with no meaning change). If material, propose "
    "the updated unit text, preserving every unchanged word exactly. Return only "
    "the JSON."
)

LABEL_PROMPT = (
    "You name clusters of unanswered advocate search questions. Each cluster is "
    "one topic. Return a short label for each cluster id, using the words the "
    "advocates used. Do not invent policy facts. Return only the JSON."
)

_UNIT = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "type": {"type": "string", "enum": ["verbatim", "policy", "procedure", "faq"]},
        "text": {"type": "string"},
        "source_span": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "domain": {"type": "string"},
        "audience": {"type": "string", "enum": ["advocate", "member", "both"]},
    },
    "required": ["title", "type", "text", "source_span", "tags", "domain", "audience"],
}

EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"units": {"type": "array", "items": _UNIT}},
    "required": ["units"],
}

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "relation": {
            "type": "string",
            "enum": ["exact", "near_duplicate", "conflict", "distinct"],
        },
        "differing_phrases": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                "required": ["a", "b"],
            },
        },
        "reason": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["relation", "differing_phrases", "reason", "confidence"],
}

SUFFICIENCY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer_unit_id": {"type": ["string", "null"]},
        "reason": {"type": "string"},
    },
    "required": ["answer_unit_id", "reason"],
}

GAP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "type": {"type": "string", "enum": ["policy", "procedure", "faq"]},
        "draft_text": {"type": "string"},
        "placeholders": {"type": "array", "items": {"type": "string"}},
        "author_checklist": {"type": "array", "items": {"type": "string"}},
        "suggested_kb": {
            "type": "string",
            "enum": ["pharmacy", "benefits", "shared-legal"],
        },
    },
    "required": [
        "title",
        "type",
        "draft_text",
        "placeholders",
        "author_checklist",
        "suggested_kb",
    ],
}

DRIFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "change": {"type": "string", "enum": ["material", "cosmetic"]},
        "summary": {"type": "string"},
        "proposed_text": {"type": "string"},
    },
    "required": ["change", "summary", "proposed_text"],
}

LABEL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["id", "label"],
            },
        }
    },
    "required": ["clusters"],
}

PROMPTS = {
    "extract_units": EXTRACT_PROMPT,
    "judge_pair": JUDGE_PROMPT,
    "assess_sufficiency": SUFFICIENCY_PROMPT,
    "draft_gap_unit": GAP_PROMPT,
    "propose_drift_fix": DRIFT_PROMPT,
    "label_clusters": LABEL_PROMPT,
}

SCHEMAS = {
    "extract_units": EXTRACT_SCHEMA,
    "judge_pair": JUDGE_SCHEMA,
    "assess_sufficiency": SUFFICIENCY_SCHEMA,
    "draft_gap_unit": GAP_SCHEMA,
    "propose_drift_fix": DRIFT_SCHEMA,
    "label_clusters": LABEL_SCHEMA,
}

# Queries the demo buttons send. The generator precomputes these with the log and the golden set.
DEMO_QUERIES = [
    ("what do I say before I quote a cost", "Pharmacy advocate"),
    ("what do I say before I quote a cost", "Insurance advocate"),
    ("how long does a part d prior auth take", "Pharmacy advocate"),
    ("how long does a part d prior auth take", "Insurance advocate"),
    ("rx price disclamer", "Pharmacy advocate"),
    ("rx price disclamer", "Insurance advocate"),
    ("do specialty drugs stay at the specialty pharmacy", "Pharmacy advocate"),
    ("do specialty drugs stay at the specialty pharmacy", "Insurance advocate"),
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixture_path(task: str, digest: str, directory: Path | None = None) -> Path:
    folder = directory or FIXTURE_DIR
    return folder / f"{task}-{digest[:12]}.json"


# Parsed fixtures, keyed by resolved directory, then (task, input sha256).
# The canonical filename for a hash wins, which matches the old scan order:
# the direct path is tried before any other file with the same hash.
_FIXTURE_INDEX: dict[str, dict[tuple[str, str], dict]] = {}
_DECISIONS: dict | None = None


def _folder_key(folder: Path) -> str:
    try:
        return str(folder.resolve())
    except OSError:
        return str(folder)


def _remember_fixture(index: dict[tuple[str, str], dict], path: Path, payload: dict) -> None:
    task = payload.get("task")
    digest = payload.get("input_sha256")
    if not isinstance(task, str) or not isinstance(digest, str):
        return
    if not path.name.startswith(f"{task}-") or not path.name.endswith(".json"):
        return
    slot = (task, digest)
    if slot not in index or path.name == f"{task}-{digest[:12]}.json":
        index[slot] = payload


def load_fixture_index(directory: Path | None = None) -> dict[tuple[str, str], dict]:
    """Fixtures in one directory, read once per process and keyed by task and input hash."""
    folder = directory or FIXTURE_DIR
    key = _folder_key(folder)
    cached = _FIXTURE_INDEX.get(key)
    if cached is not None:
        return cached
    index: dict[tuple[str, str], dict] = {}
    if folder.is_dir():
        for path in folder.glob("*.json"):
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                _remember_fixture(index, path, payload)
    _FIXTURE_INDEX[key] = index
    return index


def find_fixture(task: str, user_content: str, directory: Path | None = None):
    folder = directory or FIXTURE_DIR
    digest = sha256_text(user_content)
    return load_fixture_index(folder).get((task, digest))


def prompt_fingerprint(task: str) -> str:
    """Hash of the system prompt and the JSON schema for this task."""
    schema = json.dumps(SCHEMAS[task], sort_keys=True, separators=(",", ":"))
    return sha256_text(PROMPTS[task] + "\n" + schema)


def write_fixture(
    task: str,
    user_content: str,
    output: dict,
    input_ref: str,
    directory: Path | None = None,
    provenance: dict | None = None,
) -> Path:
    folder = directory or FIXTURE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    digest = sha256_text(user_content)
    path = fixture_path(task, digest, folder)
    payload = {
        "task": task,
        "model": MODEL,
        "generated_at": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),
        "input_sha256": digest,
        "input_ref": input_ref,
        "output": output,
    }
    if provenance:
        payload["response_id"] = provenance.get("response_id", "")
        payload["stop_reason"] = provenance.get("stop_reason", "")
        payload["usage"] = {
            "input_tokens": provenance.get("input_tokens"),
            "output_tokens": provenance.get("output_tokens"),
        }
        payload["prompt_sha256"] = provenance.get("prompt_sha256", "")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    index = _FIXTURE_INDEX.get(_folder_key(folder))
    if index is not None:
        index[(task, digest)] = payload
    return path


def _text_block(response) -> str:
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("Model declined; keep the cached output")
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise RuntimeError("Model returned no text block")


def _attach_call_context(error: BaseException, task: str, input_ref: str) -> None:
    error.add_note(f"task {task}; input {input_ref}")


def resolve_api_key() -> str:
    """Live mode key: Streamlit secrets first, then the environment. Cached mode needs neither."""
    secret = _secret_key()
    if secret:
        return secret
    return os.environ.get("ANTHROPIC_API_KEY", "") or ""


def _secret_key() -> str:
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return ""
        value = secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return ""
    return str(value or "").strip()


def call_model(task: str, user_content: str, input_ref: str = ""):
    """One structured call. Returns (parsed output, provenance).

    The API key comes from Streamlit secrets or ANTHROPIC_API_KEY.
    Provenance is stored on new fixtures. Existing fixture files are not rewritten.
    """
    import anthropic

    key = resolve_api_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=key)
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=[BETA],
            fallbacks="default",
            system=PROMPTS[task],
            messages=[{"role": "user", "content": user_content}],
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": SCHEMAS[task]},
            },
        )
    except anthropic.RateLimitError as error:
        _attach_call_context(error, task, input_ref)
        raise
    except anthropic.APIStatusError as error:
        _attach_call_context(error, task, input_ref)
        raise
    except anthropic.APIConnectionError as error:
        _attach_call_context(error, task, input_ref)
        raise
    usage = getattr(response, "usage", None)
    provenance = {
        "response_id": getattr(response, "id", "") or "",
        "stop_reason": getattr(response, "stop_reason", "") or "",
        "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
        "prompt_sha256": prompt_fingerprint(task),
    }
    return json.loads(_text_block(response)), provenance


def replay(task: str, user_content: str, live: bool = False, directory: Path | None = None):
    """Return (output, source).

    A saved answer wins over a live call. source is cached, live, missing,
    live_failed, or capped. Cached mode never calls the model.
    """
    cached = find_fixture(task, user_content, directory)
    if cached is not None:
        return cached["output"], "cached"
    if not live:
        return None, "missing"
    if not resolve_api_key():
        return None, "missing"
    from src.engine import _EXPLORE_TIMEOUT, live_slot_available, note_live_call

    if live_slot_available():
        return None, "capped"
    try:
        note_live_call()
        from src.engine import redact_query

        prompt = redact_query(user_content)
        if _EXPLORE_TIMEOUT.get():
            from concurrent.futures import ThreadPoolExecutor
            from concurrent.futures import TimeoutError as FuturesTimeout

            from src.finish import LIVE_TIMEOUT_SECONDS

            pool = ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(call_model, task, prompt)
                output, _provenance = future.result(timeout=LIVE_TIMEOUT_SECONDS)
            except FuturesTimeout:
                return {"answer_unit_id": None, "reason": "The lookup took too long."}, "timeout"
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            return output, "live"
        output, _provenance = call_model(task, prompt)
        return output, "live"
    except Exception:
        return None, "live_failed"


MISSING_CAPTION = "No cached result for this input. Turn on Live AI to run the model."
FALLBACK_CAPTION = "Live call failed; showing the cached result."


def extract_user(doc_id: str, doc_text: str) -> str:
    return f"Document ID: {doc_id}\n\n{doc_text}"


def judge_user(title_a: str, text_a: str, title_b: str, text_b: str) -> str:
    return (
        f"Statement A\nTitle: {title_a}\nText: {text_a}\n\n"
        f"Statement B\nTitle: {title_b}\nText: {text_b}"
    )


def _redact_question(text: str) -> str:
    """Redact a typed question before it is placed in a model prompt."""
    from src.engine import redact_query

    return redact_query(text or "")


def sufficiency_user(question: str, role: str, candidates: list[dict]) -> str:
    """Prompt for assess_sufficiency.

    The question is redacted here. Lexical ranking in decide() still sees the
    original question.
    """
    question = _redact_question(question)
    blocks = [f"Question: {question}", f"Role: {role}", "", "Approved units this role may read:"]
    if not candidates:
        blocks.append("(none)")
    for index, unit in enumerate(candidates):
        if index:
            blocks.append("---")
        blocks.append(f"Unit ID: {unit['unit_id']}")
        blocks.append(f"Title: {unit['title']}")
        blocks.append(f"Text: {unit['text']}")
    return "\n".join(blocks)


def gap_user(label: str, queries: list[dict], nearby: list[dict]) -> str:
    lines = [f"Cluster label: {label}", "", "Questions:"]
    for item in queries:
        lines.append(f"- {_redact_question(item['query'])} ({item['role']})")
    lines.append("")
    lines.append("Nearby approved units:")
    if not nearby:
        lines.append("(none)")
    for unit in nearby:
        lines.append(f"- {unit['unit_id']} | {unit['title']} | {unit['text']}")
    return "\n".join(lines)


def drift_user(unit_text: str, old_span: str, new_span: str) -> str:
    return (
        f"Approved unit text:\n{unit_text}\n\n"
        f"Old source span:\n{old_span}\n\n"
        f"New source span:\n{new_span}"
    )


def label_user(clusters: list[dict]) -> str:
    lines = ["Name each cluster.", ""]
    for cluster in clusters:
        lines.append(f"Cluster {cluster['id']}")
        for item in cluster["queries"]:
            lines.append(f"- {_redact_question(item['query'])} ({item['role']})")
        lines.append("")
    return "\n".join(lines).rstrip()


def check_unit(doc_text: str, unit: dict) -> dict:
    """R5 check. Never rewrites the unit."""
    span = unit.get("source_span") or ""
    text = unit.get("text") or ""
    source_mismatch = span == "" or span not in doc_text
    verbatim_altered = unit.get("type") == "verbatim" and text != span
    return {"source_mismatch": source_mismatch, "verbatim_altered": verbatim_altered}


def audience_list(value: str) -> list[str]:
    if value == "both":
        return ["advocate", "member"]
    if value == "member":
        return ["member"]
    return ["advocate"]


def load_human_decisions() -> dict:
    """Decisions from data/human_decisions.json, read once per process."""
    global _DECISIONS
    if _DECISIONS is None:
        path = ROOT / "data" / "human_decisions.json"
        if not path.exists():
            _DECISIONS = {}
        else:
            _DECISIONS = json.loads(path.read_text())
    return _DECISIONS


def kb_for(unit_id: str, doc_kb: str) -> list[str]:
    """Knowledge base from data/human_decisions.json, keyed by unit id.

    The document's knowledge base is the default when the id is absent.
    Scope is never inferred from the unit text.
    """
    assigned = (load_human_decisions().get("knowledge_bases") or {}).get(unit_id)
    if assigned:
        return list(assigned)
    return [doc_kb]


def channels_for(audience: list[str]) -> list[str]:
    if "member" in audience:
        return ["advocate_guidance", "member_chat", "website"]
    return ["advocate_guidance"]


def override_channels(override: dict, audience: list[str]) -> list[str]:
    """Channels recorded on an audience override, or the audience default."""
    recorded = override.get("channels") if isinstance(override, dict) else None
    if isinstance(recorded, list) and recorded:
        return [str(item).strip() for item in recorded if str(item).strip()]
    return channels_for(audience)


def assign_ids(doc_id: str, doc_text: str, doc_kb: str, doc_index: int, raw_units: list[dict]) -> list[dict]:
    assigned = []
    prefix = doc_id.removeprefix("SRC-")
    for index, raw in enumerate(raw_units, start=1):
        flags = check_unit(doc_text, raw)
        audience = audience_list(raw.get("audience", "advocate"))
        unit_id = f"U-{prefix}-{index:02d}"
        assigned.append(
            {
                **raw,
                "unit_id": unit_id,
                "source_doc": doc_id,
                "doc_index": doc_index,
                "index": index,
                "audience_list": audience,
                "kb_scope": kb_for(unit_id, doc_kb),
                "channels": channels_for(audience),
                **flags,
            }
        )
    return assigned


def content_tokens(text: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    return {token for token in cleaned.split() if token}


def jaccard(left: str, right: str) -> float:
    a = content_tokens(left)
    b = content_tokens(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


PAIR_THRESHOLD = 0.3
GUIDANCE_TYPES = {"policy", "procedure", "faq"}
# Unit ids are references. A quantity such as 30 in "30-day" still counts.
_UNIT_ID_RE = re.compile(r"U-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
_FIGURE_RE = re.compile(r"\$\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?")


def same_type_family(left: str, right: str) -> bool:
    if left == "verbatim" and right == "verbatim":
        return True
    return left in GUIDANCE_TYPES and right in GUIDANCE_TYPES


def is_verbatim_pricing(unit: dict) -> bool:
    """A verbatim unit that states the 30-day pricing estimate."""
    return unit.get("type") == "verbatim" and "30-day supply" in (unit.get("text") or "")


def is_website_unit(unit: dict) -> bool:
    return unit.get("source_doc") == "SRC-WEB-FAQ"


def candidate_pairs(units: list[dict]) -> list[tuple[dict, dict]]:
    """Cross-document pairs for T2.

    A pair is sent when the documents differ, the types share a family, and the
    token Jaccard is at least 0.3. Each website unit is also paired with every
    verbatim pricing unit. Domain is ignored. The earlier document is first.
    """
    pairs = []
    for index, left in enumerate(units):
        for right in units[index + 1 :]:
            if left.get("source_doc") == right.get("source_doc"):
                continue
            earlier, later = (left, right) if (left["doc_index"], left["index"]) < (right["doc_index"], right["index"]) else (right, left)
            forced = (is_website_unit(left) and is_verbatim_pricing(right)) or (
                is_website_unit(right) and is_verbatim_pricing(left)
            )
            related = same_type_family(left.get("type", ""), right.get("type", "")) and jaccard(
                left.get("text", ""), right.get("text", "")
            ) >= PAIR_THRESHOLD
            if related or forced:
                pairs.append((earlier, later))
    pairs.sort(key=lambda item: (item[0]["doc_index"], item[0]["index"], item[1]["doc_index"], item[1]["index"]))
    return pairs


def _figure_visible(figure: str, start: int, text: str) -> bool:
    """Skip outline numbers and placeholders. Keep quantities such as 30 or $505."""
    if start > 0 and text[start - 1].isdigit():
        return False
    end = start + len(figure)
    if end < len(text) and text[end].isdigit():
        return False
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start].strip()
    if prefix == "" and end < len(text) and text[end] in ".)":
        return False
    depth = 0
    for character in text[:start]:
        if character == "[":
            depth += 1
        elif character == "]" and depth:
            depth -= 1
    return depth == 0


def _figure_in_source(figure: str, source: str) -> bool:
    start = 0
    while True:
        found = source.find(figure, start)
        if found < 0:
            return False
        before = source[found - 1] if found else ""
        after_at = found + len(figure)
        after = source[after_at] if after_at < len(source) else ""
        if not before.isdigit() and not after.isdigit():
            return True
        start = found + 1


def invented_figures(draft_text: str, queries: list[str], approved_texts: list[str]) -> list[str]:
    """Numbers and dollar amounts in a draft that are absent from the questions and from approved units."""
    raw = draft_text or ""
    masked = _UNIT_ID_RE.sub(lambda match: " " * len(match.group(0)), raw)
    haystack = "\n".join([*(queries or []), *(approved_texts or [])])
    found = []
    seen = set()
    for match in _FIGURE_RE.finditer(masked):
        figure = match.group(0)
        if figure in seen or not _figure_visible(figure, match.start(), masked):
            continue
        seen.add(figure)
        if not _figure_in_source(figure, haystack):
            found.append(figure)
    return found


def with_audience_override(unit: dict, decisions: dict | None = None) -> dict:
    """Apply a human audience correction. The model output on the unit is left in place."""
    decisions = load_human_decisions() if decisions is None else decisions
    override = (decisions.get("audience_overrides") or {}).get(unit.get("unit_id"))
    if not override:
        return unit
    audience = audience_list(override.get("audience", "advocate"))
    copied = dict(unit)
    copied["audience_list"] = audience
    copied["channels"] = override_channels(override, audience)
    recorded = (decisions.get("member_texts") or {}).get(unit.get("unit_id")) or {}
    member_text = recorded.get("member_text") if isinstance(recorded, dict) else ""
    member_text = member_text or override.get("member_text") or ""
    if member_text:
        copied["member_text"] = member_text
    return copied


def search_pool(units: list[dict], pair_judgments: list[dict]) -> list[dict]:
    """Units a later search may treat as approved.

    Conflicts block both units. An exact match keeps the earlier document's unit.
    A verbatim unit that fails the source check stays out of search.
    Near-duplicates both stay until a person merges them.
    """
    by_id = {unit["unit_id"]: unit for unit in units}
    blocked = set()
    dropped = set()
    for judgment in pair_judgments:
        relation = judgment["output"]["relation"]
        left = judgment["a_id"]
        right = judgment["b_id"]
        if relation == "conflict":
            blocked.update((left, right))
        elif relation == "exact":
            dropped.add(_later_unit(by_id[left], by_id[right]))
    pool = []
    for unit in units:
        if unit["unit_id"] in blocked or unit["unit_id"] in dropped:
            continue
        if unit["source_mismatch"] or unit["verbatim_altered"]:
            continue
        pool.append(unit)
    return pool


def _later_unit(left: dict, right: dict) -> str:
    key_left = (left["doc_index"], left["index"])
    key_right = (right["doc_index"], right["index"])
    return right["unit_id"] if key_right > key_left else left["unit_id"]


def pricing_sentence(doc_text: str) -> str:
    """The Legal pricing line. 30-day is the published span. 31-day is that line after the material edit."""
    for marker in ("30-day supply", "31-day supply"):
        for line in doc_text.splitlines():
            if line.startswith("Verbatim (Legal):") and marker in line:
                return line.split("Verbatim (Legal):", 1)[1].strip()
    return ""


def prepared_drift_edits(unit_text: str, sentence: str) -> list[dict]:
    """The two edits section 5.4 precomputes. Other edits need a live call."""
    material = sentence.replace("30-day", "31-day", 1)
    if "supply at" in sentence:
        cosmetic = sentence.replace("supply at", "supply, at", 1)
    else:
        cosmetic = sentence.replace(" ", ", ", 1)
    return [
        {"name": "material", "unit_text": unit_text, "old_span": sentence, "new_span": material},
        {"name": "cosmetic", "unit_text": unit_text, "old_span": sentence, "new_span": cosmetic},
    ]
