# Harbor Health Knowledge API

Every endpoint below is implemented. The figures are illustrative, made-up data for a fictional Harbor Health. Long wording in the examples is cut with `...`, and a long list may show only the first item. The live response contains the full value.

Interactive docs are at `/api/docs`. This file is the contract.

## Run it locally

```bash
pip install -r requirements.txt -r api/requirements.txt
python -m api
```

Open `http://127.0.0.1:8000`. The process listens on `0.0.0.0`. Set `PORT` to change the port (Render sets this). Tests:

```bash
python -m pytest api/tests
```

Saved model answers in `fixtures/ai` work with no API key. Live calls read `ANTHROPIC_API_KEY` from the environment. Do not commit or print a key.

## Session and the two databases

The first request that needs a session sets an `HttpOnly` cookie named `harbor_session` (`SameSite=Lax`, `Path=/`, 14 days, `Secure` only on https). Send the cookie on later requests (`credentials: "include"` from a browser). Each cookie gets its own directory of SQLite files.

Two databases stay separate, matching the Streamlit app:

| World | File | How it is built |
| --- | --- | --- |
| `guided` | `guided.sqlite` | `POST /api/session/reset` with `start`, `short`, or `jump`. Created on first use as `start`. |
| `explore` | `explore.sqlite` | `POST /api/explore/open`. Required before any Explore sandbox read or write. |

`world` selects the database. On GET it is a query parameter. On POST it is a JSON field. The default is `guided`, except the Legal inbox, the developer portal, and routes whose path starts with `/api/explore`, which use the Explore database. An unknown world returns 400.

```json
{ "error": "world must be guided or explore." }
```

Modes:

- `start` builds the guided story at the beginning. Today's search has not run, and units are not extracted until you ask.
- `short` is the short demo. Extraction is already done. Legal still has three units to approve: `U-RX-EDU-001-09`, `U-RX-EDU-001-07`, `U-BEN-COST-001-02`.
- `jump` is the approved demo state. The Legal queue and the Knowledge Ops queue are empty.
- Explore is a separate sandbox with its own approvals, feedback, and live-call count.

Guided steps are 0 through 8: Today's problem, Extract units, Find copies, Legal approves, Search, Every channel, Gaps, Drift, Quality. The short path is steps 0, 1, 3, 4, and 5.

## Prototype limits

Explore holds the role on the session. `POST /api/explore/open` with `{ "role" }` records it. Later Explore requests use that role and ignore a `role` in the body or the query. A different role returns 403 `Open that role first.` The front end calls `open` on every role switch. Guided still accepts the role on the request, because the presenter acts as each role in turn, and the server records that acting role.

There is no identity provider. The session role is the prototype stand-in for a signed-in role. A role that is not in the product list returns 400 `Unknown role.` with `allowed` set to the list. Matching is case-insensitive. `Legal / Compliance approver` is `Legal approver`. `Member chat` is `Member`.

Verification is separate from the role. A caller is verified only after `POST /api/explore/verify` matches the member id and the date of birth on the plan file. `POST /api/explore/phone/authenticate` does the same check for one `call_id`. The `verified` field on a request is ignored. A new `call_id` needs a new check.

Guided Quality reads a frozen snapshot of the full presenter path. A fresh session reports the same tiles as step 8: 8 of 8, 4 of 4, held-out 2 of 3, and 6 misses. Explore Quality still scores the live sandbox.

## Errors

Failures are JSON. There is no stack trace. The body is a problem document and still includes `error`, which is the same sentence as `detail`.

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "Unknown role.",
  "error": "Unknown role.",
  "allowed": ["Knowledge Ops author", "Legal approver", "Pharmacy advocate", "Insurance advocate", "Member", "Knowledge owner", "Channel and AI team"]
}
```

`allowed` is present when the error is an unknown role or an unknown channel.

| Status | When |
| --- | --- |
| 400 | The action is refused, or a field is missing or invalid. |
| 403 | The session role is not allowed to do this, or Explore was opened as a different role. |
| 404 | The unit, document, version-in-time, or API path does not exist. |
| 500 | Something unexpected failed. The message is always `The service could not complete that action.` |

A bad field looks like this:

```json
{ "error": "The field unit_id is missing or invalid." }
```

An unknown `/api/...` or `/v1/...` path:

```json
{ "error": "That address is not part of the API." }
```

The browser is allowed to call this API with credentials only from `https://harbor-knowledge.onrender.com` and from localhost dev ports `5173`, `4173`, `3000`, and `8000`. Any other `Origin` is refused.

## Undo, live calls, and redaction

Every mutating action snapshots that world's database first and records the actor and the resource. `POST /api/undo` restores the latest snapshot for that world when the session role is the actor, then clears it. One level only. Undo from another role returns 403 `Only the {role} can undo this.` A publish undo appends a version and does not delete one. Reset and jump are undoable and restore the previous step. Changing the guided step with `POST /api/demo/step` clears the guided undo. A request that returns an error restores the database and keeps the previous successful undo.

Live calls stop at four caps: 20 in one database, 20 in one visit, 20 for one sandbox and one IP together, and 300 per day on the server. A new cookie does not reset the IP cap. The test client is not counted. An Explore lookup that runs longer than 6 seconds returns an abstention. A question longer than 500 characters is 400. Explore ask, guided search, and the member chat try a saved answer first. A question with no saved answer may call the model only when a key is set and that world's visit still has calls left. Guided search and Explore ask each have their own visit counter, and both caps are 20. `ai_source` is `cached`, `missing`, `live`, `live_failed`, `capped`, `no_candidates`, `closed_gap`, or `blocked`. When a cap blocks a live call, `ai_caption` is `Live call limit reached. A saved answer is used when one exists.` With no key, a question that has no saved answer stays `missing` and does not spend a cap. A guided live call that fails is returned as `missing` as well. `GET /api/portal/answers` never logs a question and never spends a live call.

Member questions and notes are passed through the same redaction as the engine before they are stored. A member id, phone number, date of birth, email, address, or a person's name becomes `[redacted]`. A name is the whole run after "my name is", "I am", "I'm", "this is", "caller", "name:", "for", or "my daughter", "son", "wife", "husband", "mother", "father", or "caregiver", and any run of two or more capitalised words that is not a drug, plan, pharmacy, or place used in the product. The first word of a sentence is kept when the rest is a single word. Drug names on the list, including Ozempic, stay.

Reads include `"illustrative": true` and `"note": "Illustrative, made-up data"`. Mutations include `"ok": true`, `"illustrative": true`, and an `undo` object:

```json
{ "available": true, "label": "Ran today's search.", "world": "guided" }
```

## Shared shapes

### Unit

Queues, search hits, the library, and version history use this object. Comma-separated fields from the database arrive as arrays. Flags are booleans.

```json
{
  "unit_id": "U-RX-EDU-001-09",
  "version": 1,
  "title": "Pricing estimate disclaimer (Legal)",
  "type": "verbatim",
  "text": "The price I quote is an estimate for a 30-day supply...",
  "tags": ["pricing", "disclaimer"],
  "tags_confirmed": true,
  "domain": "Pharmacy education, Medicare Advantage",
  "kb_scope": ["pharmacy"],
  "audience": ["advocate"],
  "channels": ["advocate_guidance", "member_chat", "voice_bot", "website"],
  "status": "approved",
  "search_visible": true,
  "source_doc": "SRC-RX-EDU-001",
  "source_quote": "The price I quote is an estimate...",
  "approved_by": "Dana Okafor (Legal)",
  "approver_role": "Legal",
  "approved_on": "2026-03-12 10:15 ET",
  "stale": false,
  "proposed_text": "",
  "requires_legal": true,
  "conflicts_with": "",
  "notes": "AI extracted.",
  "routing_reason": "",
  "source_mismatch": false,
  "verbatim_altered": false,
  "member_text": "These prices are estimates for a 30-day supply...",
  "superseded_by": "",
  "applicability": "Harbor Medicare Advantage HMO, pharmacy education calls",
  "effective_date": "2026-11-03 23:10 ET",
  "review_by": "2027-11-06",
  "document_name": "Rx education script v1"
}
```

`type` is `verbatim`, `policy`, `procedure`, or `faq`. `status` includes `proposed`, `approved`, `returned`, `superseded`, `blocked_conflict`, `merged`, and `retired`. `approver_role` is stored beside `approved_by`. Units approved before the demo, in the Explore seed and in guided `jump` and `short`, use a past `approved_on` between 2025-11-02 and 2026-10-15. Legal units are `approved_by` "Dana Okafor (Legal)" with `approver_role` "Legal". Procedures and FAQs are "Sam Patel (Knowledge Ops)" with `approver_role` "Knowledge Ops", unless `routing_reason` says the unit was routed to Legal. An approval made during the session keeps the current time and the generic label: "Legal approver" or "Knowledge Ops author", and `approver_role` matches that label. `routing_reason` is empty on a unit extracted from a document. After an author sends a gap draft or a returned unit, it is one of: `Routed to Legal: policy or verbatim type.`, `Routed to Legal: quotes approved verbatim wording from <unit title>.`, `Routed to Legal: mentions cost.`, `Routed to Legal: Legal sent it back, so Legal approves the change.`, `Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording.`

After tags are confirmed, `U-RX-EDU-001-09` records `advocate_guidance`, `member_chat`, `voice_bot`, and `website`. Explore and jump already include that list. On the short demo, confirm tags before reading the channel list. The closing unit stays on advocate guidance.

A Legal or author queue item also has `if_you_approve`:

```json
{
  "searchable_by": ["Pharmacy advocate", "Member chat"],
  "appears_in": ["advocate_guidance", "member_chat", "voice_bot", "website"],
  "replaces": "4 other wordings in Rx education script v2 (desk copy), Website FAQ",
  "approved_by": "Legal approver",
  "applies_to": "Harbor Medicare Advantage HMO, pharmacy education calls"
}
```

On the short demo, confirm tags before you treat audience as final. `U-RX-EDU-001-09` starts as audience `member` and becomes `advocate` after `POST /api/demo/confirm-tags`.

### Diff

Word-level parts, the same folding the Streamlit screens use. `kind` is `equal`, `remove`, or `add`.

```json
[
  { "kind": "equal", "text": "The price I quote is an estimate for a 30-day supply at a preferred retail pharmacy, " },
  { "kind": "remove", "text": "based on" },
  { "kind": "add", "text": "using" }
]
```

### Search result

```json
{
  "abstained": false,
  "unit": { "unit_id": "U-RX-EDU-001-09", "version": 1, "title": "Pricing estimate disclaimer (Legal)", "text": "The price I quote is an estimate..." },
  "ranked": [{ "rank": 1, "unit_id": "U-RX-EDU-001-09" }],
  "searched": ["pharmacy", "shared-legal"],
  "note": "This unit is the legal disclaimer for pricing estimates...",
  "ai_source": "cached",
  "ai_caption": "",
  "status": "",
  "blocked_note": "",
  "fallback_unit": null,
  "query": "what do I say before I quote a cost",
  "logged_query": "what do I say before I quote a cost",
  "role": "Pharmacy advocate",
  "illustrative": true
}
```

When `abstained` is true, `unit` is null. `searched` is the knowledge bases that role may read.

`status` is `blocked_conflict` when the best lexical match is blocked by an open Legal conflict. `blocked_note` is then "Under Legal review. Use the currently approved rule until Legal decides." `fallback_unit` is the approved unit it conflicts with, in the same unit shape, when one is live. Otherwise `fallback_unit` is null. The blocked wording is not returned in `unit`. The question is not added to a gap. `ai_source` is `blocked`. On any other result, `status` and `blocked_note` are empty strings.

Guided `POST /api/search` and `POST /api/search/both` add `used_live`, `live_calls_left`, and `live_calls_cap`. A saved answer is tried first. A cache miss calls the model when a key is set and the guided visit has calls left. `used_live` is true only when that call returns `ai_source` `live`. No key leaves `ai_source` `missing` and does not spend a call. A failed call is also returned as `missing`.

Role scopes:

| Role | Knowledge bases |
| --- | --- |
| Pharmacy advocate | pharmacy, shared-legal |
| Insurance advocate | benefits, shared-legal |
| Member | pharmacy, benefits |
| Knowledge Ops author, Legal approver | pharmacy, benefits, shared-legal |
| Knowledge owner | none |

After the three short-demo approvals, `what do I say before I quote a cost` returns `U-RX-EDU-001-09` for Pharmacy (pharmacy, shared-legal) and `U-BEN-COST-001-02` for Insurance (benefits, shared-legal). `how long does a part d prior auth take` abstains for both. `do specialty drugs stay at the specialty pharmacy` returns `U-RX-EDU-001-13` for Pharmacy and abstains for Insurance.

Search before any unit is approved:

```json
{ "error": "Search has nothing to read yet. Legal must approve units first." }
```

### Portal unit

```json
{
  "unit_id": "U-RX-EDU-001-09",
  "version": 1,
  "status": "approved",
  "type": "verbatim",
  "knowledge_base": ["pharmacy"],
  "applicability": "Harbor Medicare Advantage HMO, pharmacy education calls",
  "effective_date": "2026-11-03 23:10 ET",
  "review_by": "2027-11-06",
  "approved_by": "Legal approver",
  "channels": ["advocate_guidance", "member_chat", "voice_bot", "website"],
  "advocate_text": "The price I quote is an estimate...",
  "member_text": "These prices are estimates...",
  "text": "These prices are estimates...",
  "citation": "Harbor Health, pricing estimate disclaimer, version 1",
  "source": "SRC-RX-EDU-001",
  "title": "Pricing estimate disclaimer (Legal)",
  "channel": "member_chat",
  "note": "Illustrative, made-up data"
}
```

`text` is `member_text` when `channel` is `member_chat`, `voice_bot`, or `website`. Otherwise it is the advocate text. A member channel omits `advocate_text`. A requested channel that is not on the unit is 404. The citation title is the plain title: the `(Legal)` and `(Legal verbatim)` suffixes are removed, and the title is lowercased.

### Feedback record

```json
{
  "id": 12,
  "ts": "2026-11-03 23:10 ET",
  "source": "advocate",
  "role": "Pharmacy advocate",
  "kind": "couldnt_find",
  "kind_label": "Could not find it",
  "question": "[redacted] what is the price",
  "unit_id": "",
  "note": "[redacted]",
  "signals": {},
  "route": "author",
  "status": "open",
  "resolution": "",
  "resolved_on": ""
}
```

`source` is `advocate` or `channel`. Content kinds route to `author`: `couldnt_find`, `confusing_wording`, `wrong_or_outdated`, `no_answer`, `not_helpful`. Product kinds route to `product`: `hard_to_find`, `rephrased`, `clarified`, `handed_off`, `slow`.

## The website

`GET /` and any path that does not start with `api/` returns HTML. When `web/dist/index.html` exists, files are served from that build, and an unknown path returns `index.html` so the client-side router can run. Until that build exists, every page is the plain placeholder. A path that tries to leave `web/dist` returns `index.html`.

## Endpoints

### GET /api/health

No session.

```json
{ "status": "ok", "service": "harbor-knowledge", "illustrative": true, "note": "Illustrative, made-up data" }
```

### GET /api/session

Creates the guided database if needed.

```json
{
  "session_id": "9ce03b8b741345e79c0d0256a67d1bf2",
  "guided": {
    "mode": "start",
    "step": 0,
    "step_name": "Today's problem",
    "title": "Today: one disclaimer, three wordings",
    "caption": "An advocate searches for the Rx pricing disclaimer during a call.",
    "role": "Pharmacy advocate",
    "short_path": false,
    "steps": [
      { "number": 0, "name": "Today's problem", "title": "Today: one disclaimer, three wordings", "done": false, "on_short_path": true }
    ],
    "next_step": 1,
    "next_label": "Next: Extract units",
    "live_ai": false,
    "has_api_key": false,
    "undo": { "available": false, "label": "", "world": "guided" }
  },
  "explore": {
    "ready": false,
    "role": null,
    "page": null,
    "pages": [],
    "intro": "",
    "live_calls_used": 0,
    "live_calls_left": 20,
    "live_calls_cap": 20,
    "live_note": "Saved model answers are used first. A new question calls the model live.",
    "undo": { "available": false, "label": "", "world": "explore" }
  },
  "has_api_key": false
}
```

`steps` always has nine entries, numbers 0 through 8. `next_step` is null on the last step of the current path. `has_api_key` is true only when the server can see a key. It never returns the key.

### POST /api/session/reset

Body: `{ "mode": "start" }`. `mode` is `start`, `short`, or `jump`. Default `start`.

```json
{
  "ok": true,
  "message": "Demo reset to the start.",
  "demo": { "mode": "start", "step": 0, "short_path": false },
  "undo": { "available": true, "label": "Demo reset to the start.", "world": "guided" }
}
```

`short` message: `Jumped to the short demo.` `jump` message: `Jumped to the approved demo state.`

Error: `mode must be start, short, or jump.`

### POST /api/session/jump-short

No body. Same as reset with `mode: "short"`.

### GET /api/demo

The guided view from `GET /api/session`, without the session wrapper. `world` is always guided.

### POST /api/demo/step

Body: `{ "step": 4 }`. Sets the screen only. Clears the guided undo. Does not rebuild the database.

```json
{
  "ok": true,
  "demo": { "step": 4, "step_name": "Search" },
  "undo": { "available": false, "label": "", "world": "guided" }
}
```

Error: `Step must be a whole number from 0 to 8.`

### POST /api/settings/live

Body: `{ "enabled": true, "world": "guided" }`.

```json
{
  "ok": true,
  "message": "Live AI turned on.",
  "live_ai": true,
  "has_api_key": false,
  "undo": { "available": true, "label": "Live AI turned on.", "world": "guided" }
}
```

Turning it on with no key still records the flag. Calls with no saved answer stay `missing` until a key is present.

### GET /api/demo/today

Query: `world`. Before the search has been run, `ran` is false and `cards` is empty.

```json
{
  "ran": false,
  "query": "Rx pricing disclaimer",
  "message": "Run the search to see what an advocate gets today.",
  "cards": []
}
```

### POST /api/demo/today

Body optional: `{ "world": "guided" }`. An empty body is fine.

```json
{
  "ok": true,
  "message": "Ran today's search.",
  "today": {
    "ran": true,
    "query": "Rx pricing disclaimer",
    "message": "Which wording is current? Which one did Legal approve? The tool cannot say.",
    "cards": [
      {
        "title": "Rx education script v1",
        "signed": "Legal signed 2025-11-02",
        "text": "The price I quote is an estimate for a 30-day supply...",
        "diff": [{ "kind": "equal", "text": "The price I quote is an estimate..." }]
      },
      {
        "title": "Rx education script v2 (desk copy)",
        "signed": "Legal signature not recorded",
        "text": "The price I quote is an estimate for a 30-day supply...",
        "diff": [{ "kind": "equal", "text": "The price I quote is an estimate for a 30-day supply at a preferred retail pharmacy, " }, { "kind": "remove", "text": "based on" }]
      },
      {
        "title": "Website FAQ",
        "signed": "Page dated 2026-01-18",
        "text": "These prices are estimates...",
        "diff": [{ "kind": "remove", "text": "The price I quote" }]
      }
    ]
  }
}
```

The three card texts differ. Each `diff` compares that card with the v1 sentence.

### GET /api/demo/extraction

Query: `world`. Before extract, `extracted` is false, `units` is empty, and `document.body` is still the script.

```json
{
  "extracted": true,
  "tags_confirmed": false,
  "document": { "doc_id": "SRC-RX-EDU-001", "title": "Rx education script v1", "body": "# Rx Education Script..." },
  "units": [{ "unit_id": "U-RX-EDU-001-01", "number": 1, "title": "Greeting delivery guidance", "type": "procedure" }],
  "unit_count": 17,
  "verbatim_matching_source": 2,
  "verbatim_total": 2,
  "audience_corrections": [
    { "unit_id": "U-RX-EDU-001-09", "title": "Pricing estimate disclaimer (Legal)", "ai_audience": "member", "audience": "advocate", "applied": false },
    { "unit_id": "U-RX-EDU-001-15", "title": "Closing statement (Legal)", "ai_audience": "member", "audience": "advocate", "applied": false }
  ],
  "message": "AI decides units, types and spans. A person confirms tags and audience."
}
```

`applied` becomes true after confirm. `number` is the display order inside script v1.

A per-unit edit from `POST /api/demo/units/{unit_id}/tags` is shown on that unit: `tags`, `audience`, and `domain` are the edited values, and `tags_edited_by` is `Knowledge Ops author`. Other units omit `tags_edited_by`. The guided search pool still reads the confirmed unit row.

### POST /api/demo/extract

Body optional. Response: `{ "ok": true, "message": "AI extracted the units.", "extraction": { } }` where `extraction` is the GET shape with `extracted: true`. Uses the saved extraction. No live call.

### POST /api/demo/confirm-tags

Body optional.

```json
{ "ok": true, "message": "Tags and audience confirmed.", "extraction": { "tags_confirmed": true } }
```

Error if extract has not run: `Extract units before confirming tags.`

### GET /api/demo/copies

Query: `world`. Before extract:

```json
{
  "ready": false,
  "message": "No units to compare yet. Extract units from script v1 first.",
  "pairs": [],
  "counts": { "near_duplicate": 0, "exact": 0, "conflict": 0, "all": 0 }
}
```

After extract, `ready` is true. `pairs` is every model judgment, watched pairs first.

```json
{
  "ready": true,
  "canonical": false,
  "escalated": false,
  "website_merged": false,
  "can_keep_canonical": true,
  "can_escalate": false,
  "counts": { "near_duplicate": 5, "exact": 2, "conflict": 4, "all": 26 },
  "pairs": [
    {
      "a_id": "U-RX-EDU-001-09",
      "b_id": "U-RX-EDU-002-07",
      "a_title": "Pricing estimate disclaimer (Legal)",
      "b_title": "Price estimate disclaimer",
      "relation": "near_duplicate",
      "a_status": "proposed",
      "b_status": "proposed",
      "differing_phrases": [{ "a": "based on the plan records", "b": "using the plan records" }, { "a": "Your actual cost can change", "b": "What you pay can change" }],
      "diff": [{ "kind": "equal", "text": "The price I quote is an estimate " }],
      "human_line": "Prepared decision: keep the script v1 wording. It applies when you press the button."
    }
  ],
  "website_merge": {
    "into_unit_id": "U-RX-EDU-001-09",
    "member_text": "Prices on this page are estimates for a 30-day supply...",
    "units": [
      { "unit_id": "U-WEB-FAQ-01", "text": "Prices on this page are estimates...", "status": "proposed" },
      { "unit_id": "U-WEB-FAQ-02", "text": "The amount you pay may differ...", "status": "proposed" },
      { "unit_id": "U-WEB-FAQ-03", "text": "An estimate is not a guarantee of payment.", "status": "proposed" }
    ],
    "merged": false
  },
  "message": "People decide what happens next."
}
```

`counts.all` is the number of judgments. The other counts are how many of those judgments have that relation. Each pair also has `a_text`, `b_text`, `a_doc`, `b_doc`, `confidence`, `reason`, and `diff`. `human_line` is empty when no prepared decision applies. Before "keep canonical", a prepared keep says it applies when you press the button. After that action it says the human decision is in effect. `can_escalate` is true only after canonical is kept and before escalate.

### POST /api/demo/keep-canonical

Body optional.

```json
{ "ok": true, "message": "Kept the Legal-signed v1 wording. The v2 copies are superseded." }
```

Also merges the website wording into the pricing unit's member text when that merge is not already applied.

### POST /api/demo/escalate

Body optional.

```json
{
  "ok": true,
  "message": "Conflicts sent to Legal. Both versions stay blocked.",
  "conflicts": { "count_open": 3, "plans": [] }
}
```

`conflicts` is the GET `/api/conflicts` shape.

### GET /api/legal/queue

Query: `world`.

```json
{
  "ready": true,
  "count": 3,
  "waiting": [
    {
      "unit_id": "U-RX-EDU-001-09",
      "title": "Pricing estimate disclaimer (Legal)",
      "type": "verbatim",
      "status": "proposed",
      "requires_legal": true,
      "routing_reason": "",
      "if_you_approve": { "approved_by": "Legal approver", "searchable_by": ["Pharmacy advocate", "Member chat"] }
    }
  ],
  "can_approve_all": false,
  "held": [{ "unit_id": "U-BEN-COST-001-02", "title": "Cost estimate disclaimer (Legal verbatim)", "notes": "AI extracted." }],
  "approved_count": 27,
  "message": ""
}
```

On `short`, the waiting ids are exactly `U-RX-EDU-001-09`, `U-RX-EDU-001-07`, `U-BEN-COST-001-02`, in that order, and `approved_count` is 27. `approved_count` counts approved units search can show. `U-RX-EDU-PRICE-ANY` is approved for plan-data replies and is left out of this count, because `search_visible` is 0. `held` lists every unit still `proposed`, including the ones in `waiting`. When `notes` is empty the API uses `Held back as an exact copy.` `can_approve_all` is false on the short demo even when more than one unit is waiting. On `start` and `jump` it is true when more than one unit is waiting. An empty queue sets `message` to `Queue is empty. N units are approved and searchable.` Each waiting item includes `routing_reason`. It is empty for a unit extracted from a document, and it is the sentence stored by an author send for a gap unit or a returned unit.

### GET /api/author/queue

Query: `world`. Same waiting-unit shape, for procedure and faq units, plus units Legal returned. On the short demo this queue is empty. On `start`, procedure units such as `U-RX-EDU-001-01` are still waiting.

```json
{
  "count": 9,
  "waiting": [{ "unit_id": "U-RX-EDU-001-01", "title": "Greeting delivery guidance", "type": "procedure", "requires_legal": false, "routing_reason": "" }],
  "can_approve_all": true,
  "message": ""
}
```

Empty message: `Nothing waiting. Procedure and FAQ units are approved by Knowledge Ops.` Each waiting item includes `routing_reason`, empty until an author send stores one. A returned row keeps the decline reason in `notes`.

### GET /api/conflicts

Query: `world`.

```json
{
  "count_open": 1,
  "plans": [
    {
      "id": "mail-order",
      "label": "Mail-order rule",
      "open": true,
      "resolve_in_demo": true,
      "chosen_unit_id": "U-RX-EDU-001-12",
      "chosen_title": "90-day mail-order eligibility for maintenance drugs",
      "chosen_text": "For a maintenance drug, offer a 90-day mail-order supply only after...",
      "chosen_doc": "Rx education script v1",
      "retire_unit_ids": ["U-RX-EDU-002-09", "U-RX-EDU-002-10"],
      "reason_suggestion": "Legal keeps the signed script. A maintenance drug is offered as a 90-day mail order only after two retail fills in the current calendar year. The desk copy that offers mail order on the first fill is retired.",
      "recorded_reason": "",
      "comparisons": [
        {
          "unit_id": "U-RX-EDU-002-09",
          "title": "90-day mail-order on the first fill",
          "doc": "Rx education script v2 (desk copy)",
          "text": "For a maintenance drug, offer a 90-day mail-order supply on the first fill.",
          "diff": [{ "kind": "add", "text": "on the first fill." }]
        }
      ]
    }
  ],
  "message": "Both versions stay blocked until Legal picks one and records a reason."
}
```

The other plans are `greeting` (keep `U-RX-EDU-001-02`, retire `U-RX-EDU-002-01`) and `verification` (keep `U-RX-EDU-001-04`, retire `U-RX-EDU-002-03`). Only `mail-order` has `resolve_in_demo: true`. After a resolve, `open` is false and `recorded_reason` is the note that was stored.

### GET /api/legal/inbox

Query: `world`, default `explore`. One list for the Legal approver: approvals first, then open conflicts.

```json
{
  "count": 3,
  "items": [
    { "kind": "approval", "id": "U-RX-EDU-001-09", "title": "Pricing estimate disclaimer (Legal)", "routing_reason": "", "unit": { "unit_id": "U-RX-EDU-001-09", "routing_reason": "" } },
    { "kind": "conflict", "id": "mail-order", "title": "Conflict: Mail-order rule", "conflict": { "id": "mail-order", "open": true } }
  ],
  "message": "3 items await your review."
}
```

Error when Explore is not open and `world` is `explore`: `Open an Explore role before using the sandbox.` An approval item includes `routing_reason` on the item and on `unit`. It is empty for a unit extracted from a document. A conflict item has no routing reason.

### POST /api/legal/approve

Body optional. `{ "unit_id": "U-RX-EDU-001-09", "world": "guided" }`. Omit `unit_id` to approve the first waiting unit. An empty body is allowed.

```json
{
  "ok": true,
  "message": "Approved U-RX-EDU-001-09.",
  "unit_id": "U-RX-EDU-001-09",
  "queue": { "count": 2, "waiting": [] }
}
```

Errors: `The Legal queue is empty.` A unit that is not waiting, or that the author must approve: `This unit stays unapproved.` or `The Knowledge Ops author approves this unit.`

### POST /api/legal/approve-all

Body optional. Demo shortcut. Approves every unit still in the Legal queue and logs each one.

```json
{ "ok": true, "message": "Approved 12 units. Demo shortcut.", "queue": { "count": 0, "waiting": [] } }
```

Error: `The Legal queue is empty.`

### POST /api/author/approve

Body: `{ "unit_id": "U-RX-EDU-001-01", "world": "guided" }`.

```json
{
  "ok": true,
  "message": "Approved U-RX-EDU-001-01.",
  "unit_id": "U-RX-EDU-001-01",
  "queue": { "count": 0, "waiting": [] }
}
```

Errors: `A unit_id is required.` `This unit stays unapproved.` `Legal approves this unit.`

### POST /api/author/approve-all

Body optional.

```json
{
  "ok": true,
  "message": "Knowledge Ops approved 4 units (demo shortcut).",
  "approved": ["Approved U-RX-EDU-001-01."],
  "titles": ["Greeting delivery guidance"],
  "queue": { "count": 0 }
}
```

Error: `Nothing is waiting for Knowledge Ops approval.`

### GET /api/author/edits

Query: `world`. Gap drafts the author can still rewrite, and units Legal sent back.

A gap is listed when its status is `in_review` and it has no `unit_id` yet. That is a draft the knowledge owner sent to the author, and that the author has not sent to approval. A `proposed` gap stays with the owner and does not appear here. The unclustered bucket `new-unclustered` is left out of this list. A returned row is version 1 with status `returned`. `open_placeholders` on a gap, and `placeholders` on a returned unit, are the square-bracket tokens in the advocate text and the member text. `can_send` is true when the advocate text is not blank and no placeholder remains. Those tokens are what block a send.

```json
{
  "count": 10,
  "gaps": [
    {
      "id": "c5",
      "cluster": "How long a Part D prior auth takes",
      "status": "in_review",
      "draft_text": "Question: How long does a Part D prior authorization take?...",
      "draft_member_text": "",
      "draft_type": "faq",
      "unit_id": "",
      "placeholders": ["[standard decision timeframe]"],
      "open_placeholders": ["[standard decision timeframe]"],
      "invented_figures": [],
      "has_invented_figures": false,
      "live": false,
      "can_send": false
    }
  ],
  "returned": [],
  "message": ""
}
```

Empty message: `Nothing is waiting for the author to edit.` On a fresh Explore sandbox, gap c0 ("Rx pricing disclaimer to read") is already `in_review` with the reason `Asked with no approved answer; sent to the author.` The guided database leaves c0 `proposed`.

### POST /api/author/gaps/{gap_id}

Body: `{ "text": "A standard Part D prior authorization decision is made within 7 calendar days...", "member_text": "A standard prior authorization decision takes 7 calendar days...", "world": "guided" }`.

The Knowledge Ops author rewrites the advocate text and the member text. Placeholders may stay during the edit. The wording is stored as written. A question typed into search is still redacted before it is stored.

```json
{
  "ok": true,
  "message": "Edited the How long a Part D prior auth takes draft.",
  "gap": {
    "id": "c5",
    "draft_text": "A standard Part D prior authorization decision is made within 7 calendar days...",
    "draft_member_text": "A standard prior authorization decision takes 7 calendar days...",
    "placeholders": [],
    "status": "proposed"
  },
  "edits": { "count": 10, "gaps": [], "returned": [] },
  "undo": { "available": true, "label": "Edited the How long a Part D prior auth takes draft.", "world": "guided" }
}
```

Errors: `Write the unit text before saving this draft.` `That cluster is not in the queue.` `This draft can no longer be edited.` `This draft was already sent to approval.` `An approved unit cannot be edited. A change publishes a new version.`

### POST /api/author/gaps/{gap_id}/send

Body optional: `{ "world": "guided" }`.

Turns the draft into proposed unit `U-GAP-{gap_id}` with origin `gap:{gap_id}`. The gap status becomes `in_review` and stores `unit_id`. `queue` is `Legal` or `Knowledge Ops approvals`. `routing_reason` is the sentence that chose the queue.

Legal (`requires_legal` true) when any of these is true: the type is `policy` or `verbatim`; the advocate text or member text contains the text of an approved unit whose type is `verbatim` or whose `requires_legal` is true, after whitespace is collapsed and curly quotes are folded to straight quotes, and that text is a full sentence or longer; the advocate text or member text mentions a dollar amount (`$35`, `$1,200.00`) or a whole word from cost, costs, price, prices, pricing, copay, copays, copayment, coinsurance, deductible, premium, out-of-pocket, MOOP. The first match wins, in that order. A `procedure` or `faq` with none of those goes to Knowledge Ops approvals.

```json
{
  "ok": true,
  "message": "Sent U-GAP-c5 to Knowledge Ops approvals.",
  "unit_id": "U-GAP-c5",
  "queue": "Knowledge Ops approvals",
  "routing_reason": "Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording.",
  "gap": { "id": "c5", "status": "in_review", "unit_id": "U-GAP-c5" },
  "unit": {
    "unit_id": "U-GAP-c5",
    "status": "proposed",
    "type": "faq",
    "requires_legal": false,
    "routing_reason": "Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording."
  },
  "undo": { "available": true, "label": "Sent the draft to approval.", "world": "guided" }
}
```

Gap `c0` in the Explore database, "Which Rx pricing disclaimer to read and when", is an FAQ that quotes the approved pricing disclaimer. With its placeholder filled, the same call returns:

```json
{
  "queue": "Legal",
  "routing_reason": "Routed to Legal: quotes approved verbatim wording from Pricing estimate disclaimer (Legal)."
}
```

A remaining bracketed placeholder blocks the send. The refusal names the open placeholders, up to six, then how many more remain:

```json
{
  "error": "Replace every bracketed placeholder before sending this to approval. Still open: [standard decision timeframe], [expedited decision timeframe], and 4 more."
}
```

Sending `new-unclustered` is refused with `Group these questions into a topic first.` Other errors: `That cluster is not in the queue.` `This draft is not waiting to be sent.` `This draft was already sent to approval.` `Write the unit text before sending this to approval.`

An Explore draft with `needs_source` set stays unsent until every placeholder is grounded and filled. The refusal is `Ground and fill every placeholder before sending this draft.` The unit that send creates lists those sources on `sources`, and Legal sees them on the queue when the draft routes there.

On approval the unit becomes searchable, the gap is marked `closed`, and `POST /api/search` returns that unit for each of the gap's original questions when the caller's knowledge bases overlap the unit. `ai_source` is `closed_gap`. A member call to `GET /api/portal/answers` returns the member text, a citation, and `ai_source` `closed_gap`.

### POST /api/author/units/{unit_id}

Body: `{ "text": "Read this updated line to the member.", "member_text": "Here is the plain example for a member.", "world": "guided" }`.

The same edit for version 1 of a unit whose status is `returned`. Placeholders may stay. Any other status is refused, including `approved`.

```json
{
  "ok": true,
  "message": "Edited U-RX-EDU-001-08 after Legal sent it back.",
  "unit": { "unit_id": "U-RX-EDU-001-08", "version": 1, "status": "returned", "text": "Read this updated line to the member." },
  "edits": { "count": 1, "returned": [{ "unit_id": "U-RX-EDU-001-08", "can_send": true }] },
  "undo": { "available": true, "label": "Edited U-RX-EDU-001-08 after Legal sent it back.", "world": "guided" }
}
```

Errors: `A unit_id is required.` `Write the unit text before saving this draft.` `That unit is not in the queue.` `Only a unit Legal sent back can be edited here.` `An approved unit cannot be edited. A change publishes a new version.`

### POST /api/author/units/{unit_id}/send

Body optional: `{ "world": "guided" }`.

Sets a `returned` unit back to `proposed`. The same routing rule as a gap send applies, and a unit that needed Legal before it was sent back always returns to Legal (`Routed to Legal: Legal sent it back, so Legal approves the change.` when no other Legal reason applies). The rule never lowers a gate. A quote match ignores the unit's own approved text. The same placeholder block applies. `U-RX-EDU-001-08` is a procedure whose wording contains "pricing", so it returns to Legal with the cost reason.

```json
{
  "ok": true,
  "message": "Sent U-RX-EDU-001-08 to Legal.",
  "unit_id": "U-RX-EDU-001-08",
  "queue": "Legal",
  "routing_reason": "Routed to Legal: mentions cost.",
  "unit": { "unit_id": "U-RX-EDU-001-08", "status": "proposed", "requires_legal": true, "routing_reason": "Routed to Legal: mentions cost." },
  "undo": { "available": true, "label": "Sent U-RX-EDU-001-08 back to approval.", "world": "guided" }
}
```

Errors: `A unit_id is required.` `This unit is not waiting to be sent back to approval.` `Write the unit text before sending this to approval.` `Replace every bracketed placeholder before sending this to approval. Still open: [plain example].`

### POST /api/author/drift/resolve

Body: `{ "note": "Keep the signed 30-day wording.", "world": "guided" }`.

The Knowledge Ops author clears the stale flag on the approved version Legal sent back. The live text stays the current version. The note is required.

```json
{
  "ok": true,
  "message": "Resolved the returned drift fix for U-RX-EDU-001-09. The approved version stays live.",
  "unit_id": "U-RX-EDU-001-09",
  "note": "Keep the signed 30-day wording.",
  "stale": false,
  "unit": { "unit_id": "U-RX-EDU-001-09", "version": 1, "status": "approved", "stale": false },
  "undo": { "available": true, "label": "Resolved the returned drift fix. The approved version stays live.", "world": "guided" }
}
```

Errors: `A note is required.` `No drift fix is waiting for the author.` `The approved version is no longer the one Legal sent back.`

### POST /api/legal/decline

Body: `{ "unit_id": "U-RX-EDU-001-09", "reason": "Needs a plainer member sentence.", "world": "guided" }`.

```json
{ "ok": true, "message": "Returned U-RX-EDU-001-09 to the author.", "queue": { "count": 2 } }
```

The unit's status becomes `returned` and it shows in the author queue with the reason in `notes`.

Errors: `A unit_id is required.` `A reason is required.` `This unit is not in the Legal queue.`

### POST /api/conflicts/resolve

Body: `{ "conflict_id": "mail-order", "reason": "Legal keeps the signed script.", "world": "guided" }`. Omit `conflict_id` to resolve the open plan with `resolve_in_demo: true`.

```json
{ "ok": true, "message": "Kept U-RX-EDU-001-12.", "conflicts": { "count_open": 2 } }
```

The chosen unit can be approved later. The retired units leave search. Errors: `A reason is required.` `No conflict is waiting for that decision.`

### GET /api/search/prompts

No session.

```json
{
  "cost": "what do I say before I quote a cost",
  "abstain": "how long does a part d prior auth take",
  "misspell": "rx price disclamer",
  "pharmacy_only": "do specialty drugs stay at the specialty pharmacy",
  "roles": ["Pharmacy advocate", "Insurance advocate"]
}
```

### POST /api/search

Body: `{ "role": "Pharmacy advocate", "query": "what do I say before I quote a cost", "record": true, "world": "guided" }`.

`record` defaults to true. A recorded search writes the activity log and can add the question to the gap cluster. `record: false` does not snapshot and does not undo.

```json
{
  "ok": true,
  "message": "Searched as Pharmacy advocate.",
  "result": { "abstained": false, "unit": { "unit_id": "U-RX-EDU-001-09" }, "searched": ["pharmacy", "shared-legal"], "ai_source": "cached" },
  "undo": { "available": true, "label": "Searched as Pharmacy advocate.", "world": "guided" }
}
```

With `record: false` the body is `{ "ok": true, "result": { }, "undo": { "available": false, "world": "guided" } }` and `undo.available` reflects whatever snapshot was already there.

Errors: `Enter a question.` `Unknown role.` `Use POST /api/explore/member for a member question. This search returns advocate wording.` Plus the empty-library error above.

Advocate roles: `Pharmacy advocate`, `Insurance advocate`, `Knowledge Ops author`, `Legal approver`, `Knowledge owner`. `Member` is rejected here.

### POST /api/search/both

Body: `{ "query": "what do I say before I quote a cost", "record": true, "world": "guided" }`. Runs Pharmacy advocate, then Insurance advocate.

```json
{
  "ok": true,
  "message": "Searched as both roles.",
  "query": "what do I say before I quote a cost",
  "results": [
    { "role": "Pharmacy advocate", "abstained": false, "unit": { "unit_id": "U-RX-EDU-001-09" }, "searched": ["pharmacy", "shared-legal"] },
    { "role": "Insurance advocate", "abstained": false, "unit": { "unit_id": "U-BEN-COST-001-02" }, "searched": ["benefits", "shared-legal"] }
  ]
}
```

### GET /api/channels

Query: `world`. The live pricing disclaimer and the previous version, plus a preview of the prepared publish.

```json
{
  "ready": true,
  "revised": false,
  "live": { "unit_id": "U-RX-EDU-001-09", "version": 1, "text": "The price I quote is an estimate...", "member_text": "These prices are estimates..." },
  "previous": null,
  "advocate_diff": [],
  "member_diff": [],
  "revision_ready": true,
  "revision_preview": {
    "find": "based on the plan records I can see today",
    "replace": "based on the plan records available on this call",
    "advocate_text": "The price I quote is an estimate...",
    "advocate_diff": [{ "kind": "remove", "text": "I can see today" }, { "kind": "add", "text": "available on this call" }],
    "member_text": "These prices are estimates...",
    "member_diff": [],
    "next_version": 2
  },
  "message": "Live everywhere: U-RX-EDU-001-09 version 1"
}
```

Before the pricing unit is approved, `ready` is false, `live` is null, and `message` is `No channel has an approved pricing disclaimer yet. Legal must approve it first.`

`live.channels` for `U-RX-EDU-001-09`, once tags are confirmed, is `advocate_guidance`, `member_chat`, `voice_bot`, and `website`. The same four values are on `GET /api/portal/units/U-RX-EDU-001-09` and on the quick-start `sample_unit`. `voice_bot` uses the member text, the same way `member_chat` and `website` do. A published revision copies that channel list onto the new version.

After publish, `revised` is true, `previous` is version 1 with `status: "superseded"`, and `live.version` is 2. `advocate_diff` and `member_diff` compare previous with live.

### POST /api/channels/publish

Body optional. Publishes the next version of the pricing unit to advocate guidance, member chat, and the website. The find/replace is the prepared channel revision. Version 1 becomes `superseded`.

```json
{
  "ok": true,
  "message": "Published version 2 to every channel.",
  "channels": { "ready": true, "revised": true, "live": { "version": 2 }, "previous": { "version": 1, "status": "superseded" } }
}
```

A second publish that would not change the wording returns 400 `That wording is already published.` Pass `idempotency_key` to receive the first response again without a new version. Publish writes a `unit.revised` event with `ts`, `version`, and `previous_version`. Undo of that publish appends a retraction and a new version that restores the earlier wording. It does not delete version 2.

Error: `The pricing disclaimer is not approved yet.` `That wording is already published.`

### GET /api/units/expired

Query: `world`. Approved units whose `review_by` date is before today.

```json
{
  "count": 1,
  "units": [{ "unit_id": "U-RX-EDU-001-13", "title": "Specialty drugs stay at the specialty pharmacy", "review_by": "2026-01-15", "status": "approved" }],
  "message": "1 approved unit past the review date."
}
```

`jump` and `explore` include `U-RX-EDU-001-13`. A start database that has not approved it returns `count: 0` and `No approved unit is past its review date.`

### GET /api/units

Query: `world`, `kb`, `status`, `type`, `q`, `role`, `latest` (default true).

`latest: true` keeps the highest version of each unit. `role` of `Pharmacy advocate` or `Insurance advocate` limits the list to approved units in that role's knowledge bases. `q` matches title or text.

```json
{
  "count": 1,
  "units": [{ "unit_id": "U-RX-EDU-001-09", "status": "approved", "kb_scope": ["pharmacy"] }],
  "filters": { "kb": "pharmacy", "status": "approved", "type": "", "q": "", "role": "Pharmacy advocate", "latest": true }
}
```

### GET /api/units/{unit_id}

Query: `world`.

```json
{
  "unit": { "unit_id": "U-RX-EDU-001-09", "version": 2, "if_you_approve": { "approved_by": "Legal approver" } },
  "versions": [{ "version": 1, "status": "superseded", "approved_by": "Legal approver", "effective_date": "2026-11-03 23:10 ET" }],
  "copies": [{ "unit_id": "U-RX-EDU-002-04", "status": "superseded" }]
}
```

`unit` is the current row (approved preferred, otherwise the latest version). 404: `No unit U-NOPE.`

### GET /api/units/{unit_id}/versions

Query: `world`.

```json
{
  "unit_id": "U-RX-EDU-001-09",
  "versions": [
    { "version": 1, "status": "superseded", "diff_from_previous": { "advocate": [], "member": [] } },
    {
      "version": 2,
      "status": "approved",
      "diff_from_previous": {
        "advocate": [{ "kind": "remove", "text": "I can see today" }, { "kind": "add", "text": "available on this call" }],
        "member": [{ "kind": "remove", "text": "we have today" }]
      }
    }
  ],
  "moments": ["2026-11-03 23:04 ET", "2026-11-03 23:10 ET"]
}
```

404: `No unit {id}.`

### GET /api/units/{unit_id}/as-of

Query: `timestamp` (required), `world`. A date with no time means the end of that day. The timestamp may be RFC 3339 (`2026-09-24T10:00:00Z`) or `YYYY-MM-DD HH:MM ET`. A value the server cannot read returns 400. The result is the latest approved version whose effective time is at or before that moment. Two versions published in the same minute share a timestamp, so the later version is the one that was live. `versions_that_day` lists every version whose live interval overlaps that calendar day, each with `start` and `end`. `end` is empty while that version is still the latest.

```json
{
  "unit_id": "U-RX-EDU-001-09",
  "version": 2,
  "text": "The price I quote is an estimate...",
  "member_text": "These prices are estimates...",
  "approver": "Legal approver",
  "effective_date": "2026-11-03 23:10 ET",
  "versions_that_day": [
    { "version": 1, "start": "2026-11-03 23:04 ET", "end": "2026-11-03 23:10 ET" },
    { "version": 2, "start": "2026-11-03 23:10 ET", "end": "" }
  ],
  "note": "Illustrative, made-up data"
}
```

Errors: `A timestamp is required.` `Use a timestamp like 2026-09-24T10:00:00Z or 2026-09-24 10:00 ET.` 404 `No version was live at that time.`

### GET /api/documents

Query: `world`.

```json
{
  "documents": [
    { "doc_id": "SRC-BEN-COST-001", "title": "Benefits cost guide", "legal_signed": "Legal last signed: 2025-10-14", "kb": "benefits", "unit_count": 9, "name": "Benefits cost guide" },
    { "doc_id": "SRC-RX-EDU-001", "title": "Rx education script", "legal_signed": "Legal last signed: 2025-11-02", "kb": "pharmacy", "unit_count": 17, "name": "Rx education script v1" },
    { "doc_id": "SRC-RX-EDU-002", "title": "Rx education script, desk copy", "legal_signed": "Legal last signed: not recorded", "kb": "pharmacy", "unit_count": 14, "name": "Rx education script v2 (desk copy)" },
    { "doc_id": "SRC-WEB-FAQ", "title": "Website FAQ excerpt", "legal_signed": "Page date: 2026-01-18", "kb": "pharmacy", "unit_count": 6, "name": "Website FAQ" }
  ]
}
```

There are four documents. `unit_count` is version-1 units from that source.

### GET /api/documents/{doc_id}

Query: `world`.

```json
{
  "doc_id": "SRC-RX-EDU-001",
  "title": "Rx education script",
  "name": "Rx education script v1",
  "legal_signed": "Legal last signed: 2025-11-02",
  "kb": "pharmacy",
  "body": "# Rx Education Script...",
  "units": [{ "unit_id": "U-RX-EDU-001-01", "number": 1, "title": "Greeting delivery guidance" }]
}
```

404: `No document SRC-NOPE.`

Explore also loads three sandbox documents: `SRC-SPEC-SOP-001`, `SRC-PA-FAQ-001`, and `SRC-CALLBACK-001`. Each unit includes `status`, `routing_reason`, and `source_span`. `source_span` is an exact substring of `body`. When that span is in the body, the unit also includes `span_start` and `span_end`. An attested source, `SRC-ATTEST-{n}`, adds `signer`, `owner_role`, `statement`, and `attested_on`. The guided library does not include these documents. Figures in the sandbox documents are illustrative.

### GET /api/gaps

Query: `world`.

```json
{
  "count": 10,
  "gaps": [
    {
      "id": "c5",
      "cluster": "How long a Part D prior auth takes",
      "query_example": "how long does a part d prior auth take",
      "search_count": 3,
      "roles": ["Pharmacy advocate", "Insurance advocate"],
      "draft_title": "How long a Medicare Part D prior authorization takes",
      "draft_text": "Question: How long does a Part D prior authorization take?...",
      "draft_member_text": "",
      "draft_type": "faq",
      "unit_id": "",
      "suggested_kb": "pharmacy",
      "status": "proposed",
      "placeholders": ["[standard decision timeframe]"],
      "checklist": ["Confirm the standard and expedited decision timeframes..."],
      "queries": ["how long does a part d prior auth take"],
      "invented_figures": [],
      "has_invented_figures": false,
      "live": false,
      "findability": false,
      "reason": ""
    }
  ],
  "message": ""
}
```

Empty message: `AI found no unanswered cluster in the search log.` Status moves to `in_review`, `process_fix`, `dismissed`, or `closed`.

Each gap has `kind`. `new-unclustered` ("New, not yet clustered") is `unclustered`. Every other gap is `cluster`.

`placeholders` are the square-bracket tokens in the stored list, the draft text, and the member text, in that order, without duplicates. A comma inside the brackets stays part of the token. `invented_figures` lists figures the draft added that are not in the question or an approved unit. `has_invented_figures` is true when that list is not empty.

`findability` is true when the cluster's questions paraphrase an approved unit. Those seeded clusters are "Rx pricing disclaimer to read", "Closing line for Rx education call", "Greeting for MA pharmacy education call", and "Member website wording for drug price estimate". `search_count` on a seeded cluster is an illustrative weekly volume. The top content gap is 340. The other seeded clusters are from 12 to 210. Counts are illustrative. Gap `c0` stays available for the authoring walkthrough.

A cluster id that starts with `live-` has `live` true. It is written when Live AI is on, a recorded search abstains, and the redacted question matches no existing cluster. The label is that redacted question. A saved draft wins. A missing, capped, or failed draft, including live mode with no API key, stays in `new-unclustered` ("New, not yet clustered"). Cached mode uses that bucket. `POST /api/search` with `record: false` does not draft. A question that already belongs to a cluster only increments that cluster. `POST /api/gaps/{gap_id}` returns the same gap list, including any live cluster.

### POST /api/gaps/{gap_id}

Body: `{ "action": "write", "reason": "The team should draft this next.", "world": "guided" }`. `action` is `write`, `fix_process`, or `dismiss`.

```json
{
  "ok": true,
  "message": "Draft sent to the author.",
  "gaps": { "count": 10, "gaps": [{ "id": "c5", "status": "in_review", "reason": "The team should draft this next." }] }
}
```

`fix_process` message: `Marked as a process fix.` `dismiss` message: `Cluster dismissed.` Search still has no approved answer for that question. Errors: `Unknown gap action. Use write, fix_process, or dismiss.` `A reason is required.` `That cluster is not in the queue.`

### GET /api/drift

Query: `world`.

```json
{
  "unit_id": "U-RX-EDU-001-09",
  "live_text": "The price I quote is an estimate...",
  "live_version": 1,
  "member_text": "These prices are estimates...",
  "stale": false,
  "proposed_text": "",
  "material": false,
  "cosmetic": false,
  "sent": false,
  "material_line": "",
  "cosmetic_line": "",
  "summary": "",
  "cosmetic_summary": "",
  "change": "",
  "ai_source": "",
  "events": [],
  "prepared": {
    "cosmetic": {
      "old_span": "The price I quote is an estimate for a 30-day supply at a preferred retail pharmacy...",
      "new_span": "The price I quote is an estimate for a 30-day supply, at a preferred retail pharmacy...",
      "diff": [{ "kind": "remove", "text": "supply" }, { "kind": "add", "text": "supply," }]
    },
    "material": {
      "old_span": "The price I quote is an estimate for a 30-day supply at a preferred retail pharmacy...",
      "new_span": "The price I quote is an estimate for a 31-day supply at a preferred retail pharmacy...",
      "diff": [{ "kind": "remove", "text": "30-day" }, { "kind": "add", "text": "31-day" }]
    }
  },
  "ready": true,
  "message": "Cached mode knows two prepared edits: a cosmetic comma, and 30-day supply to 31-day supply."
}
```

The prepared spans are the saved edits. A cosmetic edit logs an event and leaves `stale` false. A material edit sets `stale` true and keeps the approved text live. After send, `sent` is true and the message is `Sent to Legal. The approved version stays live.` If the pricing unit is not approved, `ready` is false and the message is `Drift needs an approved pricing disclaimer to watch.`

Each event is a `drift_log` row: `ts`, `unit_id`, `version`, `kind` (`cosmetic` or `material`), `change`, `old_span`, `new_span`, `summary`, `proposed_text`, `flagged` (boolean), `ai_source`, and `status`.

### POST /api/drift

Body: `{ "kind": "cosmetic", "world": "guided" }` or `"kind": "material"`.

```json
{ "ok": true, "message": "Sent to Legal: a comma inside Legal wording. The approved version stays live.", "drift": { "cosmetic": true, "stale": false } }
```

That message is the prepared cosmetic edit, the comma inside the verbatim pricing sentence. A cosmetic edit outside a verbatim span still returns `Cosmetic edit logged. Nothing was flagged.`

Material message: `Source edited. The unit is flagged stale.` The drift object then has `material: true` and `stale: true`.

Errors: `Use material or cosmetic.` `Approve the disclaimer before a source change can be compared.` `No cached result for this input. Turn on Live AI to run the model.`

### POST /api/drift/send

Body optional.

```json
{ "ok": true, "message": "Sent to Legal. The approved version stays live.", "drift": { "sent": true, "stale": true } }
```

Error when no material edit is waiting: `No material change is waiting for Legal.`

### GET /api/legal/drift

Query: `world`. Material drift rows with status `sent`. These items stay out of `GET /api/legal/queue` and `GET /api/legal/inbox`.

```json
{
  "count": 1,
  "items": [
    {
      "id": 1,
      "unit_id": "U-RX-EDU-001-09",
      "version": 1,
      "old_wording": "The price I quote is an estimate for a 30-day supply...",
      "new_wording": "The price I quote is an estimate for a 31-day supply...",
      "source_before": "30-day supply",
      "source_after": "31-day supply",
      "summary": "The supply length changed from 30 days to 31 days.",
      "member_text": "These prices are estimates for a 30-day supply..."
    }
  ],
  "message": ""
}
```

Empty message: `No drift fix is waiting for Legal.` `old_wording` is the live approved text. `new_wording` is the proposed text.

### POST /api/legal/drift/approve

Body optional: `{ "world": "guided" }`.

Only the Legal approver, which this route is. Publishes the proposal as the next approved version. The previous version is superseded. The new version is searchable. Channels and knowledge bases are copied. The old source span is replaced once in the member text and the source quote when it is present.

```json
{
  "ok": true,
  "message": "Published U-RX-EDU-001-09 version 2 from the source change. Every channel now shows version 2.",
  "unit_id": "U-RX-EDU-001-09",
  "version": 2,
  "drift": { "count": 0, "items": [], "message": "No drift fix is waiting for Legal." },
  "unit": { "unit_id": "U-RX-EDU-001-09", "version": 2, "status": "approved", "stale": false, "channels": ["advocate_guidance", "member_chat", "voice_bot", "website"] },
  "undo": { "available": true, "label": "Published the drift fix. Every channel now shows that version.", "world": "guided" }
}
```

Errors: `No drift fix is waiting for Legal.` `The approved version is no longer live.` `The drift fix has no proposed wording.`

### POST /api/legal/drift/return

Body: `{ "reason": "The 30-day supply is still the signed wording.", "world": "guided" }`.

Only the Legal approver, which this route is. The reason must be non-empty. The approved version stays live and stays marked stale.

```json
{
  "ok": true,
  "message": "Sent the drift fix for U-RX-EDU-001-09 back. The approved version stays live.",
  "unit_id": "U-RX-EDU-001-09",
  "reason": "The 30-day supply is still the signed wording.",
  "stale": true,
  "drift": { "count": 0, "items": [], "message": "No drift fix is waiting for Legal." },
  "undo": { "available": true, "label": "Sent the drift fix back. The approved version stays live.", "world": "guided" }
}
```

Errors: `A reason is required.` `No drift fix is waiting for Legal.`

The author clears that stale flag with `POST /api/author/drift/resolve`.

### GET /api/quality

Query: `world`. Before score:

```json
{ "scored": false, "message": "Score the golden set and the duplicate variants with the saved model answers." }
```

This read does not set the scored flag. Insights on Explore compute the same report for the owner view and also leave the flag alone.

### POST /api/quality/score

Body optional. Scores with saved answers. No live call.

```json
{
  "ok": true,
  "message": "Scored the golden set.",
  "quality": {
    "scored": true,
    "held_out_pass": 2,
    "held_out_total": 3,
    "open_conflicts": [{ "id": "mail-order", "label": "Mail-order rule" }],
    "message": "Held-out questions 2 of 3 pass. 3 open conflicts blocked for Legal. 7 model misses kept visible.",
    "tiles": [
      { "key": "hit_at_1", "label": "hit@1", "display": "88%", "detail": "7 of 8", "note": "Illustrative, made-up data" },
      { "key": "correct_abstain", "label": "correct abstentions", "display": "100%", "detail": "4 of 4" },
      { "key": "over_abstain", "label": "over-abstentions", "display": "12%", "detail": "1 of 8" },
      { "key": "leaks", "label": "cross-role leaks", "display": "0", "detail": "0 leaks" },
      { "key": "dedup_precision", "label": "dedup precision", "display": "100%", "detail": "11 of 11" },
      { "key": "dedup_recall", "label": "dedup recall", "display": "100%", "detail": "11 of 11" }
    ],
    "verbatim_source": { "label": "Verbatim units matching source", "ok": 5, "total": 5, "display": "5 of 5", "note": "Illustrative, made-up data. Count from the T1 source check." },
    "golden_table": {
      "columns": ["Question", "Role", "Expected", "Got", "Result"],
      "rows": [{ "Question": "what do I say before I quote a cost", "Role": "Pharmacy advocate", "Expected": "U-RX-EDU-001-09", "Got": "U-RX-EDU-001-09", "Result": "Pass", "reason": "...", "ai_source": "cached", "heldout": "no" }],
      "held_out": [
        {
          "Question": "Can I talk about the drug and the price when a caregiver has no authorization on the account?",
          "Role": "Pharmacy advocate",
          "Expected": "U-RX-EDU-001-05",
          "Got": "ABSTAIN",
          "Result": "Fail",
          "reason": "U-RX-EDU-001-05 says to check the caregiver's authorization...",
          "ai_source": "cached",
          "heldout": "yes"
        }
      ]
    },
    "dedup_table": {
      "columns": ["variant text", "label", "AI judgment", "AI reason", "Result"],
      "rows": [{ "variant_text": "...", "label": "near_duplicate", "judgment": "near_duplicate", "reason": "...", "result": "Pass" }],
      "precision": 1,
      "recall": 1
    },
    "misses": [{ "miss": "T3 abstained on 'Can I talk about the drug and the price when a caregiver has no authorization on the account?' for Pharmacy advocate. The golden set expects U-RX-CAREGIVER-AUTH (U-RX-EDU-001-05).", "next_step": "Check the candidate list before changing the prompt, and leave the miss on the Quality screen." }],
    "scored_questions": 12,
    "held_out_questions": 3,
    "extraction_boundary": { "matched": 16, "missed": 0, "extra": 1, "extra_unit_ids": ["U-RX-EDU-001-01"], "rows": [], "note": "Illustrative, made-up data. Labels were written after the first model run." }
  }
}
```

The held-out table has three rows. Exactly one fails: the caregiver question above, expected `U-RX-EDU-001-05`, got `ABSTAIN`. The owner kept that row as a visible miss. Guided Quality does not depend on which steps were clicked. It scores a frozen snapshot of the full path, so a fresh session and step 8 both read 8 of 8, 4 of 4, held-out 2 of 3, and 6 misses. A leaks tile with zero answers says `not measured`. Each rate includes a Wilson 95% interval. Explore adds slices by role, by intent, and a robustness slice. Those slices are illustrative and do not change the guided numbers. Treat every `display` as illustrative.

`score_counts` is on the scored report:

```json
{ "right_first": 7, "wrong": 0, "wrong_no_answers": 1, "scored": 8, "not_scored": 0 }
```

`right_first`, `wrong`, and `wrong_no_answers` sum to `scored`. `scored` is the answerable golden rows that had a saved answer. `not_scored` counts rows whose `Result` is `No saved answer`, including held-out rows. Those rows are not passes and they are not listed in `misses`. Insights uses this same object.

### POST /api/feedback

Body:

```json
{
  "source": "advocate",
  "role": "Pharmacy advocate",
  "kind": "couldnt_find",
  "question": "member id H12345678 what is the price",
  "unit_id": "U-RX-EDU-001-09",
  "note": "dob 01/02/1950",
  "signals": { "searches_in_call": 2 },
  "world": "guided"
}
```

```json
{
  "ok": true,
  "message": "Flag sent. Member details are removed before it is stored.",
  "feedback": {
    "id": 4,
    "question": "[redacted] what is the price",
    "note": "[redacted]",
    "route": "author",
    "status": "open",
    "kind": "couldnt_find",
    "kind_label": "Could not find it"
  }
}
```

Errors: `Feedback source must be advocate or channel.` `A role is required.` `Unknown feedback kind 'nope'.`

### GET /api/feedback/author

Query: `world`. Open content feedback grouped for the author.

```json
{
  "groups": [
    { "kind": "couldnt_find", "count": 1, "examples": ["[redacted] what is the price"], "ids": [4] }
  ]
}
```

### GET /api/feedback/product

Query: `world`.

```json
{
  "total": 1,
  "groups": [{ "kind": "clarified", "count": 1, "examples": ["How much will my prescription cost?"], "ids": [8] }],
  "message": ""
}
```

Empty message: `Nothing open.`

### GET /api/feedback/open

Query: `route` (`author` or `product`, default `author`), `world`.

```json
{ "route": "author", "count": 1, "items": [{ "id": 4, "status": "open", "kind": "couldnt_find" }] }
```

Error: `route must be author or product.`

### GET /api/feedback/summary

Query: `world`. Counts for the current week, Monday through Sunday, America/New_York. Open and resolved both count.

```json
{
  "week_start": "2026-11-02",
  "by_kind": [{ "kind": "couldnt_find", "count": 2, "label": "Could not find it" }],
  "most_flagged": [{ "unit_id": "U-RX-EDU-001-09", "count": 3, "kinds": ["confusing_wording", "not_helpful"] }]
}
```

### POST /api/feedback/{feedback_id}/resolve

Body: `{ "resolution": "Rewrote the member sentence.", "world": "explore" }`.

```json
{
  "ok": true,
  "message": "Resolved.",
  "feedback": { "id": 4, "status": "resolved", "resolution": "Rewrote the member sentence.", "resolved_on": "2026-11-03 23:20 ET" }
}
```

Errors: `A resolution note is required.` The engine's message when the id is unknown or already resolved.

### GET /api/activity

Query: `world`, `limit` (default 12, max 100).

```json
{
  "events": [
    { "ts": "2026-11-03 23:10 ET", "role": "Legal approver", "message": "Approved U-RX-EDU-001-09. Search can see this unit: Yes." }
  ]
}
```

Newest first. `limit` is the number of rows returned.

### GET /api/undo

Query: `world`.

```json
{ "available": true, "label": "Ran today's search.", "world": "guided", "screen": 0, "restore_screen": 0 }
```

When nothing is stored: `{ "available": false, "label": "", "world": "guided" }`.

### POST /api/undo

Body: `{ "world": "guided" }`. Restores the snapshot and clears undo for that world. The guided response includes `demo`. The Explore response includes `explore`.

```json
{
  "ok": true,
  "message": "Undid: Ran today's search.",
  "world": "guided",
  "demo": { "mode": "short", "step": 0 },
  "undo": { "available": false, "label": "", "world": "guided" }
}
```

Error: `Nothing to undo.` A second undo in a row returns that error. Undo after reset restores the mode and step from before the reset.

## Explore

Roles: `Knowledge Ops author`, `Legal approver`, `Pharmacy advocate`, `Insurance advocate`, `Member`, `Knowledge owner`, `Channel and AI team`.

Pages by role:

| Role | Pages |
| --- | --- |
| Knowledge Ops author | My work, Library, Source documents, Copies and conflicts |
| Legal approver | Review inbox, Revise wording, Version history |
| Pharmacy advocate | Agent desktop, What I can read |
| Insurance advocate | Agent desktop, What I can read |
| Member | App chat, Website, Phone line |
| Knowledge owner | Insights, Gaps, Drift, Quality |
| Channel and AI team | Quick start, API reference, Change events, Product backlog |

Opening a role resets the Explore database to the `explore` build, clears the visit cache, and sets the live-call count to 0. Switching role without reset keeps the same database and only changes the page list.

### POST /api/explore/open

Body: `{ "role": "Pharmacy advocate" }`.

```json
{
  "ok": true,
  "explore": {
    "ready": true,
    "role": "Pharmacy advocate",
    "page": "Agent desktop",
    "pages": ["Agent desktop", "What I can read"],
    "intro": "You are on a live call. The knowledge panel already shows the approved answer for the call reason.",
    "live_calls_used": 0,
    "live_calls_left": 20,
    "live_calls_cap": 20
  }
}
```

Error: `Unknown Explore role.`

### GET /api/explore

The same `explore` object. `ready` is false until open.

### POST /api/explore/page

Body: `{ "page": "What I can read" }`. The page must be one of the current role's pages.

```json
{ "ok": true, "explore": { "page": "What I can read" } }
```

Errors: `Open an Explore role before using the sandbox.` `That page is not in this role's workspace.`

### POST /api/explore/reset

No body. Rebuilds the sandbox, keeps the role, returns to that role's first page, and clears caches and the visit live count. The reset itself can be undone.

```json
{ "ok": true, "message": "Sandbox reset.", "explore": { "ready": true, "live_calls_used": 0 } }
```

Error: `Open an Explore role before resetting the sandbox.`

### POST /api/explore/ask

Body: `{ "role": "Pharmacy advocate", "query": "what do I say before I quote a cost" }`. Optional `member_id` and `verified` (default false). Saved answer first. The role must not be `Member`. Without `member_id`, the response is the search result below.

With `member_id`, a drug-price or visit-cost question uses plan data when `verified` is true. The response keeps `result` and adds `kind` (`price` or `visit_cost`), the `price` or `visit_cost` payload, and `units` in advocate text. A comparison question ("cheaper", or "mail" together with "retail") also adds `price_options`: the 30-day and 90-day prices at preferred retail, standard retail, and mail order, each with the disclaimer for that combination. An unknown `member_id` is 404.

When `verified` is false and the question is a drug price or a visit cost, the response is the approved unverified-caller rule and no figures: `text` and `units` only, with no `result`, `price`, `visit_cost`, or `price_options`.

```json
{
  "ok": true,
  "message": "Searched the sandbox.",
  "result": { "abstained": false, "unit": { "unit_id": "U-RX-EDU-001-09" }, "ai_source": "cached", "searched": ["pharmacy", "shared-legal"] },
  "used_live": false,
  "from_visit_cache": false,
  "live_calls_left": 20,
  "live_calls_cap": 20
}
```

The same role and query later in the visit returns the stored payload with `from_visit_cache: true` and does not spend another live call. A question with no fixture and no key returns `ai_source: "missing"` and `used_live: false`. At 20 visit calls, a new question is not sent to the model.

Errors: `Enter a question.` `Unknown role.` `Use POST /api/explore/member for a member question.` `Open an Explore role before using the sandbox.`

### GET /api/explore/questions

Query: `role` (required).

```json
{
  "role": "Pharmacy advocate",
  "questions": [
    "what do I say before I quote a cost",
    "rx price disclamer",
    "how long does a part d prior auth take",
    "Do specialty drugs stay at the specialty pharmacy?"
  ]
}
```

An unknown role returns an empty `questions` array.

### GET /api/explore/calls

Query: `role` (required). Pharmacy and Insurance only. The members are fictional.

```json
{
  "role": "Pharmacy advocate",
  "knowledge_bases": ["pharmacy", "shared-legal"],
  "calls": [
    {
      "reason": "Drug price question",
      "member": "Dana R.",
      "plan": "Harbor Medicare Advantage HMO",
      "detail": "Asking what a 30-day fill of a maintenance drug will cost at a retail pharmacy.",
      "verified": true,
      "questions": ["what do I say before I quote a cost"],
      "fictional": true
    }
  ]
}
```

Error: `That role has no agent desktop.`

### POST /api/explore/desk

Body: `{ "role": "Pharmacy advocate", "query": "how long does a part d prior auth take", "call_reason": "Prior authorization status" }`. Same search as ask, plus call counting.

```json
{
  "ok": true,
  "result": { "abstained": true, "ai_source": "cached" },
  "searches_in_call": 1,
  "feedback_recorded": ["no_answer"]
}
```

On the third search in the visit for that role, `hard_to_find` is recorded once for that role and `call_reason`. An abstention records `no_answer` once for that role and query. Those automatic writes are their own undo step (`Feedback captured.`).

Errors: `The agent desktop is for Pharmacy and Insurance advocates.` `Enter a question.`

### POST /api/explore/member

Body is `{ "topic": 2 }`, `{ "question": "Do specialty drugs go through mail order?" }`, or both. `member_id` is optional. When it is omitted, the signed-in member is Dana R. (`HBR-20418`). An unknown `member_id` is 404. Topic wins when `topic` is present. Topic buttons do not record feedback.

Topics 0 and 1 are plan-data clarifies, described below. Topics 2, 3, and 4 return `kind: "topic"` with the approved member wording. This example is topic 3:

Topic response:

```json
{
  "ok": true,
  "kind": "topic",
  "abstained": false,
  "reply": "Specialty drugs stay at Harbor Specialty Pharmacy. They are not moved to mail order. Source: Harbor Health, specialty drugs not converted to mail order, version 1",
  "member_text": "Specialty drugs stay at Harbor Specialty Pharmacy. They are not moved to mail order.",
  "citation": "Source: Harbor Health, specialty drugs not converted to mail order, version 1",
  "title": "Specialty drugs not converted to mail order",
  "version": 1,
  "unit_id": "U-RX-EDU-001-13",
  "question": "Can my specialty drug come by mail?",
  "suggestions": [],
  "live_calls_left": 20,
  "feedback_recorded": null,
  "illustrative": true
}
```

A topic reply does not include `undo` or `show_unit_id`. Question replies set `show_unit_id` to false. The reply text uses the plain title. Do not render `unit_id` in the member bubble. The field is there so the client can send it to the helped endpoint.

Question outcomes:

| Situation | kind | What the member sees |
| --- | --- | --- |
| Drug price, or "is this drug covered" | `price` | One sentence from the drug-price fields, plus `units` and `chips` |
| Visit cost | `visit_cost` | One sentence from the visit-cost fields, plus `units` and `chips` |
| Drug or visit intent, with the drug or visit type missing | `clarify` | "Which drug? Here are the ones on your list." or "What kind of visit?" and `chips` |
| Referral, and no cost word: "referral" or "refer", or specialist, cardiologist, cardiology, dermatologist | `answer` | `U-BEN-COST-001-05` member wording and its citation. "do i need a referral for a cardiologist" uses this row. |
| A family or caregiver word (daughter, son, wife, husband, spouse, partner, caregiver, family, someone) with "call", "calling", or "talk" | `answer` | `U-RX-EDU-001-05` member wording and its citation. "can my son call for me" uses this row. |
| Billing or a complaint: overcharged, charged, bill, billing, upset, angry, complaint, wrong, refund | `handoff_offer` | "I'm sorry about that. A member advocate can look at your account with you." Chips are "Talk to a member advocate" and "See my recent claims". Not recorded as a gap. |
| No plan, billing, family, or complaint word | `out_of_scope` | "I can help with your Harbor plan: drug prices, visit costs, referrals and pharmacy questions, or I can connect you with a member advocate." Not recorded as a gap. |
| Saved answer | `answer` | Member wording plus `Source: Harbor Health, {plain title}, version {n}` |
| Abstain on the knowledge path | `clarify` | `I want to give you the right answer.` plus up to two topic suggestions |
| No saved answer, live failed, or capped | `handoff` | `I cannot look that up right now. Try a topic, or I can connect you with a member advocate.` |

Plan-data replies run before the knowledge search and do not call the model. They do not record a gap, a search, or feedback. `How much will my prescription cost?` and topic 0 clarify with the member's drugs as `chips`. `What will my doctor visit cost?` and topic 1 clarify with the visit types. `how much is atorvastatin` returns `kind: "price"`. `what is the weather` is `out_of_scope`. `Do specialty drugs go through mail order?` still answers from `U-RX-EDU-001-13` with `ai_source: "cached"`. A knowledge-path clarify records feedback kind `clarified`. Handoff records `handed_off`. Those two are undoable on their own.

A drug-price match needs a formulary name, or the word prescription, drug, or medication, plus a cost word (`how much`, cost, price, pay, copay, cheaper). "Mail" together with "retail" also counts as a cost word. "Is X covered" is also `price`, and it uses the tier and the preferred 30-day price. Days are 90 when the question contains `90`, and 30 otherwise. Pharmacy is mail order for "mail", standard retail for "standard", specialty for "specialty", and preferred retail otherwise. A question with "cheaper", or with both "mail" and "retail", is a comparison. A visit-cost match needs doctor, primary care, specialist, cardiology, cardiologist, urgent care, emergency, or ER, plus a cost word. A plain "doctor visit" asks which kind. Specialist, cardiology, and cardiologist are a specialist visit.

The plan words that keep a question in scope are plan, drug, medication, prescription, pharmacy, refill, price, cost, copay, pay, covered, coverage, doctor, visit, specialist, referral, claim, deductible, insulin, mail, card, benefit, and every formulary name. Plurals of those words count. A billing or complaint word, or a family word, also keeps the question out of the out-of-scope reply. Out of scope is used only when none of those words appear. A cost word still chooses a price or visit intent before the referral intent, so "what will a specialist visit cost" stays `visit_cost`.

```json
{
  "ok": true,
  "message": "Member reply ready.",
  "kind": "clarify",
  "abstained": true,
  "reply": "I want to give you the right answer. Is this about drug price estimates or someone calling for me? Tap a topic, or I can connect you with a member advocate.",
  "suggestions": [
    { "index": 0, "label": "Drug price estimates", "question": "How much will my prescription cost?" },
    { "index": 4, "label": "Someone calling for me", "question": "Can my daughter call about my drugs?" }
  ],
  "unit_id": "",
  "ai_source": "cached",
  "feedback_recorded": "clarified",
  "from_visit_cache": false,
  "show_unit_id": false,
  "live_calls_left": 20,
  "live_calls_cap": 20
}
```

Topics:

| index | label | question |
| --- | --- | --- |
| 0 | Drug price estimates | How much will my prescription cost? |
| 1 | Cost of a doctor visit | What will my doctor visit cost? |
| 2 | Specialist referrals | Do I need a referral to see a specialist? |
| 3 | Specialty pharmacy | Can my specialty drug come by mail? |
| 4 | Someone calling for me | Can my daughter call about my drugs? |

Errors: `Enter a question or choose a topic.` `Unknown topic.` `Open an Explore role before using the sandbox.` `No member HBR-00000.`

Price reply:

```json
{
  "ok": true,
  "message": "Member reply ready.",
  "kind": "price",
  "abstained": false,
  "reply": "Atorvastatin 20 mg, 30-day supply at a preferred pharmacy: $0.",
  "price": {
    "drug": { "drug_id": "atorvastatin", "name": "Atorvastatin", "strength": "20 mg tablet", "tier": 1, "specialty": false },
    "pharmacy": "preferred_retail",
    "days": 30,
    "available": true,
    "price": 0,
    "price_display": "$0",
    "tier_label": "Tier 1",
    "coverage_stage": "Initial coverage",
    "note": "",
    "withheld_reason": "",
    "units": [
      {
        "unit_id": "U-RX-EDU-001-09",
        "version": 1,
        "title": "Pricing estimate disclaimer",
        "text": "These prices are estimates...",
        "citation": "Source: Harbor Health, pricing estimate disclaimer, version 1"
      }
    ],
    "illustrative": true
  },
  "units": [
    {
      "unit_id": "U-RX-EDU-001-09",
      "version": 1,
      "title": "Pricing estimate disclaimer",
      "text": "These prices are estimates...",
      "citation": "Source: Harbor Health, pricing estimate disclaimer, version 1"
    }
  ],
  "chips": ["How much is a 90-day supply of atorvastatin by mail?"],
  "question": "how much is atorvastatin",
  "suggestions": [],
  "show_unit_id": false,
  "feedback_recorded": null,
  "illustrative": true
}
```

`text` on a unit reference is the member wording on these routes. `title` drops a trailing `(Legal)` or `(Legal verbatim)`. The citation uses that title in lower case. Visit-cost replies use the same envelope with `visit_cost` in place of `price`. A clarify reply sets `chips` to full questions and does not include `price` or `visit_cost`.

For `kind` `price` and `kind` `visit_cost`, `read_order` is `["units", "reply"]`. Read every unit in `units` before the `reply`. The reply holds the amount. The same field is on `GET /api/portal/answers` for those kinds, and on a verified advocate ask.

`kind` `safety` is returned before any other member intent for emergency and crisis language. The reply is the approved safety unit. The question is stored redacted in `safety_signals` and is not added to the gap list.

`kind` `authenticate` is the automated line (`channel` `voice_bot`) before the caller completes `POST /api/explore/phone/authenticate`. It carries the approved IVR prompt and no member-specific figures. `GET /api/explore/member/topics` includes `ivr_prompts` with `authenticate`, `before_amount`, `advocate`, and `add_caller`.

`kind` `plan_figure` answers an out-of-pocket question from plan data. `units` is the approved disclaimer. If that unit is missing, the kind is `handoff` and `withheld_reason` says the figure stays hidden.

A complaint offers reason chips before the advocate chip. Each reason returns an approved unit, or a handoff when no unit covers it. A caregiver asking for a price receives the caregiver rule and no price.

### GET /api/explore/member/profile

Query: `member_id` (required). Explore only. 404 for an unknown member. 400 when `member_id` is missing.

```json
{
  "member": { "member_id": "HBR-20418", "name": "Dana R.", "plan": "Harbor Medicare Advantage HMO" },
  "plan": {
    "name": "Harbor Medicare Advantage HMO",
    "premium": { "amount": 0, "display": "$0 a month" },
    "primary_care": { "amount": 0, "display": "$0" },
    "specialist": { "amount": 35, "display": "$35" },
    "urgent_care": { "amount": 45, "display": "$45" },
    "emergency": { "amount": 110, "display": "$110" },
    "out_of_network": { "display": "Not covered except emergency and urgent care", "exceptions": ["emergency", "urgent_care"] },
    "medical_deductible": { "amount": 0, "display": "$0" },
    "out_of_pocket_maximum": { "amount": 4500, "display": "$4,500" },
    "part_d_deductible": { "amount": 250, "display": "$250", "note": "Does not apply to tiers 1 and 2" },
    "pharmacies": [{ "name": "Harbor Preferred Pharmacy", "network": "preferred", "city": "Harbor City", "display": "Preferred" }]
  },
  "coverage_stage": "Initial coverage",
  "oop": { "limit": 4500, "spent": 1210, "limit_display": "$4,500", "spent_display": "$1,210" },
  "drug_deductible": { "amount": 250, "met": false },
  "drugs": [{ "drug_id": "atorvastatin", "name": "Atorvastatin", "strength": "20 mg tablet", "tier": 1, "specialty": false }],
  "claims": [
    {
      "date": "2026-10-02",
      "provider_type": "Primary care",
      "amount_billed": 180,
      "amount_billed_display": "$180",
      "plan_paid": 180,
      "plan_paid_display": "$180",
      "member_paid": 0,
      "member_paid_display": "$0",
      "status": "Paid"
    }
  ],
  "recent_contacts": [{ "date": "2026-10-28", "channel": "Phone", "summary": "Asked what a 30-day fill of a maintenance drug costs at a retail pharmacy." }],
  "illustrative": true,
  "note": "Illustrative, made-up data"
}
```

There is one member for each caller in the advocate scenarios: Dana R. `HBR-20418`, Luis M. `HBR-22841`, Grace T. `HBR-23107`, Ken W. `HBR-24055`, Maria S. `HBR-25112`, Robert A. `HBR-26390`, Ann P. `HBR-27004`. Dana R. is the signed-in member. Each record has three claims and three recent contacts. `plan.pharmacies` lists three illustrative pharmacies marked preferred or standard.

### GET /api/explore/member/drug-price

Query: `member_id` (required), `drug_id` (required), `pharmacy` (`preferred_retail`, `standard_retail`, `mail_order`, or `specialty`; default `preferred_retail`), `days` (`30` or `90`; default `30`).

```json
{
  "drug": { "drug_id": "atorvastatin", "name": "Atorvastatin", "strength": "20 mg tablet", "tier": 1, "specialty": false },
  "pharmacy": "preferred_retail",
  "days": 30,
  "available": true,
  "price": 0,
  "price_display": "$0",
  "tier_label": "Tier 1",
  "coverage_stage": "Initial coverage",
  "note": "",
  "withheld_reason": "",
  "units": [
    {
      "unit_id": "U-RX-EDU-001-09",
      "version": 1,
      "title": "Pricing estimate disclaimer",
      "text": "These prices are estimates...",
      "citation": "Source: Harbor Health, pricing estimate disclaimer, version 1"
    }
  ],
  "illustrative": true
}
```

`units` includes one approved price disclaimer. A 30-day supply at `preferred_retail` uses `U-RX-EDU-001-09`. Every other pharmacy and days combination uses `U-RX-EDU-PRICE-ANY` ("Drug price estimate disclaimer (any supply or pharmacy)"). That unit is approved, `search_visible` is false, and search never returns it. Member text is "This is an estimate for the supply and pharmacy shown, based on the plan information we have today. The amount you pay may differ if the pharmacy, the days' supply, or your stage of coverage changes. An estimate is not a guarantee of payment." Advocate text is "The price I quote is an estimate for the supply and pharmacy we discussed, based on the plan records I can see today. Your actual cost can change if the pharmacy, the days' supply, or your stage of coverage is different. This estimate is not a guarantee of payment." A specialty drug at any pharmacy other than `specialty` sets `available` false, `price` null, `note` to `Specialty drugs fill at Harbor Specialty Pharmacy.`, and also includes `U-RX-EDU-001-13`. A combination the price table leaves empty sets `available` false, `price` null, and `note` to `This supply is not available at that pharmacy.` Adalimumab at the specialty pharmacy for 30 days is `price` 612, `price_display` `$612`, and `note` `33% coinsurance, shown as $612.` Insulin glargine uses the insulin row, so a preferred 30-day fill is `$35` with `tier_label` `Tier 3`.

If the disclaimer for that supply and pharmacy has no approved version with the wording for the route, `available` is false, `price` is null, `price_display` is empty, `units` is empty, and `withheld_reason` is `Prices appear once Legal approves the pricing disclaimer.` Approval is enough for `U-RX-EDU-PRICE-ANY`, because that unit stays out of search on purpose.

Errors: `A member_id is required.` `A drug_id is required.` `No member HBR-00000.` `No drug not-a-drug.` `Unknown pharmacy.` `Days must be 30 or 90.`

### GET /api/explore/member/visit-cost

Query: `member_id` (required), `visit` (`primary_care`, `specialist`, `urgent_care`, or `emergency`), `network` (`in` or `out`; default `in`).

```json
{
  "visit": "specialist",
  "network": "in",
  "available": true,
  "cost": 35,
  "cost_display": "$35",
  "note": "You need a referral from your primary care doctor first.",
  "withheld_reason": "",
  "units": [
    {
      "unit_id": "U-BEN-COST-001-02",
      "version": 1,
      "title": "Cost estimate disclaimer",
      "text": "This cost is an estimate...",
      "citation": "Source: Harbor Health, cost estimate disclaimer, version 1"
    },
    {
      "unit_id": "U-BEN-COST-001-05",
      "version": 1,
      "title": "HMO specialist visits require a referral",
      "text": "A specialist visit on a Harbor Medicare Advantage HMO needs a referral from your primary care doctor before the visit.",
      "citation": "Source: Harbor Health, hmo specialist visits require a referral, version 1"
    }
  ],
  "illustrative": true
}
```

`units` includes the cost disclaimer `U-BEN-COST-001-02` when `available` is true. When `available` is false, the cost disclaimer is omitted, because no cost is shown. A specialist visit also includes the referral rule `U-BEN-COST-001-05`, including an out-of-network specialist visit that shows no cost. An in-network specialist sets `note` to `You need a referral from your primary care doctor first.` Out of network is not covered except `emergency` and `urgent_care`, which use the same illustrative copay as in network. The note for a visit that is not covered is `Out of network is not covered, except emergency and urgent care.`

If the cost disclaimer has no approved, search-visible version with member wording, `available` is false, `cost` is null, `cost_display` is empty, `units` is empty, and `withheld_reason` is `Costs appear once Legal approves the cost disclaimer.`

Errors: `A visit is required.` `Unknown visit.` `Network must be in or out.`

### GET /api/explore/member-record

Query: `member_id` (required), `role` (`Pharmacy advocate` or `Insurance advocate`), `verified` (`true` or `false`; default `false`).

The body is the profile shape, plus `role`, `verified`, `prices`, `units`, and `withheld_reason`. `prices` is one preferred-retail 30-day quote for each drug on the member's list, so those rows use `U-RX-EDU-001-09`. Any other supply or pharmacy on a price route uses `U-RX-EDU-PRICE-ANY`. `units` use advocate wording. A specialty drug that cannot fill at preferred retail keeps `available` false and the specialty note, and `units` also includes `U-RX-EDU-001-13`.

When `verified` is false, the response drops `drugs[].tier`, `prices`, `claims`, and `oop`. `withheld_reason` is the advocate text of the approved unit titled "No coverage details to unverified callers", and that unit is the only entry in `units`.

```json
{
  "verified": false,
  "role": "Pharmacy advocate",
  "withheld_reason": "Do not quote a copay, a tier, or a coverage limit to an unverified caller, and do not say whether a drug is on the formulary.",
  "units": [
    {
      "unit_id": "U-RX-EDU-001-07",
      "version": 1,
      "title": "No coverage details to unverified callers",
      "text": "Do not quote a copay, a tier, or a coverage limit to an unverified caller, and do not say whether a drug is on the formulary.",
      "citation": "Source: Harbor Health, no coverage details to unverified callers, version 1"
    }
  ],
  "illustrative": true
}
```

A non-advocate role returns 400 `Unknown role.` The same member and drug errors as the profile apply. Prices on a verified record are withheld, with the pricing-disclaimer sentence, when `U-RX-EDU-001-09` has no approved version with advocate wording.

### POST /api/explore/member/helped

Body: `{ "helped": true, "question": "Do specialty drugs go through mail order?", "unit_id": "U-RX-EDU-001-13" }`.

`helped: true` does not write:

```json
{ "ok": true, "message": "Thanks. Your feedback goes to the knowledge team.", "recorded": false }
```

`helped: false` stores kind `not_helpful` from source `channel`, role `Member`, with the question redacted.

```json
{
  "ok": true,
  "message": "Thanks. Your feedback goes to the knowledge team.",
  "recorded": true,
  "feedback": { "kind": "not_helpful", "route": "author", "status": "open", "question": "Do specialty drugs go through mail order?" }
}
```

Error when `helped` is false and the question is blank: `A question is required.`

### GET /api/explore/member/topics

Requires an open Explore database.

```json
{
  "topics": [
    {
      "index": 0,
      "label": "Drug price estimates",
      "question": "How much will my prescription cost?",
      "available": true,
      "member_text": "These prices are estimates...",
      "citation": "Source: Harbor Health, pricing estimate disclaimer, version 1",
      "version": 1,
      "effective_date": "2026-11-03",
      "slug": "drug-price-estimates",
      "phone_reading": "These prices are estimates..."
    }
  ],
  "message": "The same approved member wording is used by the app, the website, and the phone line."
}
```

`phone_reading` is the member text, or `I do not have an approved answer for that. Please hold while I connect you with a member advocate.` when the unit has no member wording.

### GET /api/explore/my-work

Knowledge Ops author only, once an Explore role is open. Another open role receives `Only the Knowledge Ops author can do this.` A closed Explore database still returns `Open an Explore role before using the sandbox.`

The queue has four groups:

- Documents to review
- Unanswered questions
- Source changes
- Sent back by Legal

A group with no items is left out of `groups` and named in `empty_groups`. Advocate and channel flags stay on `GET /api/feedback/author` and on Insights. This queue does not list them.

```json
{
  "count": 8,
  "items": [
    { "group": "Documents to review", "id": "doc-SRC-SPEC-SOP-001", "title": "Specialty pharmacy intake SOP", "kind": "document", "document": { "doc_id": "SRC-SPEC-SOP-001", "waiting_for_ko": 5 } },
    { "group": "Unanswered questions", "id": "gap-gap-pa-time", "title": "How long does a standard prior authorization decision take?", "kind": "gap", "gap": { "id": "gap-pa-time" } },
    { "group": "Source changes", "id": "drift-1", "title": "Callback hours changed from 5:00 p.m. to 6:00 p.m. Eastern. These hours are illustrative.", "kind": "drift", "drift": { "id": 1, "unit_id": "U-CB-HOURS" } }
  ],
  "groups": [{ "group": "Documents to review", "count": 3, "items": [] }],
  "empty_groups": ["Sent back by Legal"],
  "waiting_on_legal": [{ "id": "mail-order", "label": "Mail-order rule" }],
  "message": ""
}
```

Item `kind` is `document`, `gap`, `drift`, or `returned`. A returned item includes `unit`. Empty message when nothing is waiting: `Nothing needs you right now.`

### POST /api/author/units/{unit_id}/review

Knowledge Ops author only. Explore only.

Body:

```json
{
  "world": "explore",
  "action": "approve",
  "reason": "",
  "text": null,
  "member_text": null,
  "type": null,
  "tags": null,
  "audience": null
}
```

`action` is `approve`, `send_to_legal`, `edit`, or `reject`.

- `approve` is allowed when the routing rule gives the unit to Knowledge Ops. The unit becomes `approved` and search-visible in Explore. A unit routed to Legal returns `This unit goes to Legal: {routing reason}.`
- `send_to_legal` moves the unit to the Legal queue with its routing reason. Knowledge Ops can send any waiting unit, including one the rule would let Knowledge Ops approve.
- `edit` saves new wording, type, tags, or audience. The unit stays waiting for Knowledge Ops. An edit does not lower a Legal gate that is already set.
- `reject` needs a reason of at least four words. The unit becomes `rejected` and is never searchable.

Each decision records the actor, the time, and the action.

```json
{
  "ok": true,
  "message": "Recorded approve on U-SOP-REFERRAL.",
  "unit_id": "U-SOP-REFERRAL",
  "action": "approve",
  "status": "approved",
  "decision": {
    "actor": "Knowledge Ops author",
    "action": "approve",
    "ts": "2026-11-05 19:40 ET",
    "reason": "",
    "detail": ""
  },
  "unit": { "unit_id": "U-SOP-REFERRAL", "status": "approved", "search_visible": true }
}
```

Errors: `That unit is not in the sandbox queue.` `This unit is not waiting for Knowledge Ops.` `A rejection needs a reason of at least four words.` `Send the wording, type, tags, or audience to edit.` `This route is for the explore sandbox.` `Only the Knowledge Ops author can do this.`

### GET /api/author/documents

Knowledge Ops author only. Explore only.

Query: `world=explore`. `all=true` includes every document. Without it, a document is listed when it still has a unit waiting for Knowledge Ops or a unit Legal sent back.

```json
{
  "count": 3,
  "documents": [
    {
      "doc_id": "SRC-SPEC-SOP-001",
      "title": "Specialty pharmacy intake SOP",
      "name": "Specialty pharmacy intake SOP",
      "kb": "pharmacy",
      "waiting_for_ko": 5,
      "with_legal": 0,
      "sent_back": 0,
      "approved": 0,
      "rejected": 0,
      "blocked": 0
    }
  ]
}
```

`waiting_for_ko` counts status `extracted`. `with_legal` counts status `with_legal` and proposed units that require Legal. `sent_back` counts `returned`. `approved`, `rejected`, and `blocked` count those statuses on the latest version.

### GET /api/legal/documents

Legal approver only. Explore only.

Lists each document that has units waiting for Legal, with `waiting` as the count. The list includes units Knowledge Ops sent with `send_to_legal`, regulated units Knowledge Ops edited and resent, and the existing seeded Legal items.

```json
{
  "count": 2,
  "documents": [
    {
      "doc_id": "SRC-SPEC-SOP-001",
      "title": "Specialty pharmacy intake SOP",
      "name": "Specialty pharmacy intake SOP",
      "kb": "pharmacy",
      "waiting": 1
    }
  ]
}
```

A Knowledge Ops session receives `Only the Legal approver can do this.`

### POST /api/author/gaps/{gap_id}/placeholders/{index}/source

Knowledge Ops author only. Explore only. `index` is 0-based.

Body:

```json
{ "world": "explore", "kind": "document", "ref": "SRC-PA-FAQ-001", "quote": "A standard prior authorization decision takes 4 business days after Harbor receives a complete request. An expedited request takes 24 hours. These figures are illustrative." }
```

`kind` is `unit`, `document`, or `request`.

- `unit` and `document`: `quote` must be an exact substring of that approved unit, or of that document. Otherwise `That passage is not in the source.`
- `request`: creates a source request to `owner_role` with `question`, status `pending`.

```json
{
  "ok": true,
  "message": "Grounded the placeholder.",
  "gap_id": "gap-pa-time",
  "index": 0,
  "placeholders": [
    { "index": 0, "token": "[standard decision time]", "kind": "document", "ref": "SRC-PA-FAQ-001", "quote": "...", "request_id": "", "filled_text": "", "sourced": true, "filled": false }
  ]
}
```

### POST /api/author/gaps/{gap_id}/placeholders/{index}/fill

Knowledge Ops author only. Explore only.

Body: `{ "world": "explore", "text": "4 business days" }`.

Allowed only when that placeholder has a source. The text must appear in the cited passage or statement, ignoring case and whitespace. Otherwise `That fact is not in the cited source.` A placeholder with no source returns `Ground this placeholder in a source before filling it.`

### GET /api/explore/source-requests

Knowledge Ops author only. Explore only.

```json
{
  "count": 1,
  "requests": [
    {
      "id": "SR-1",
      "gap_id": "gap-insulin-mail",
      "placeholder_index": 0,
      "owner_role": "Pharmacy Operations",
      "question": "Is a 90-day insulin supply available by mail?",
      "status": "pending",
      "statement": "",
      "signer": "",
      "doc_id": "",
      "mark": "",
      "answered_at": ""
    }
  ]
}
```

### POST /api/explore/source-requests/{id}/answer

Knowledge Ops author only. In the sandbox the Knowledge Ops author may play the owner. The record is marked `Simulated owner reply`.

Body: `{ "world": "explore", "statement": "A 90-day insulin supply by mail is available after two retail fills. This figure is illustrative.", "signer": "Riley Chen" }`.

The answer creates attested document `SRC-ATTEST-{n}` with a title, the statement, the signer, the owner role, and the date. `GET /api/documents/{doc_id}` returns it.

```json
{
  "ok": true,
  "message": "Simulated owner reply.",
  "request": { "id": "SR-1", "status": "answered", "doc_id": "SRC-ATTEST-1", "mark": "Simulated owner reply", "signer": "Riley Chen" }
}
```

### POST /api/author/gaps/{gap_id}/no-source

Knowledge Ops author only. Explore only. Used when no one owns the fact.

Body: `{ "world": "explore", "reason": "No team owns appointment transportation." }`.

The gap returns to the Knowledge owner as a process gap. The label is `The business has no answer yet`. Advocates keep the no-answer. A search that abstains on that exact question adds `follow_up`: `The business has no answer yet. Follow up with the knowledge owner.`

```json
{
  "ok": true,
  "message": "The business has no answer yet.",
  "gap_id": "gap-ride",
  "status": "process_gap",
  "label": "The business has no answer yet",
  "reason": "No team owns appointment transportation."
}
```

Insights lists these gaps on `process_gaps`.

### Gap candidates in `GET /api/author/edits`

Each sandbox gap draft carries `candidate`: what the AI found when it searched every Harbor document for the question. Older drafts carry `null`.

```json
{ "kind": "document", "ref": "SRC-WEB-MAIL-001", "quote": "You can get up to a 90-day supply ...", "fill": "", "trust": "unreviewed",
  "trust_label": "Public website copy, not reviewed by Knowledge Ops or Legal", "note": "...", "owner_role": "Pharmacy Operations",
  "source_name": "Member website: mail-order pharmacy page", "source_status": "Not reviewed. Public website copy.", "illustrative": true }
```

`trust` is `review_backlog` (a Harbor document nobody has reviewed yet), `unreviewed` (text such as website copy), or `none` (nothing found; `ref` is empty). `fill` is the words the AI would put in the placeholder, taken from `quote`, or empty. The candidate grounds a placeholder only through `POST .../placeholders/{index}/source`, so the same substring rule applies.

`SRC-WEB-MAIL-001` is a made-up copy of a member website page. It has no units and is never searchable; it exists so the AI can cite it.

### Answering a source request with no policy

`POST /api/explore/source-requests/{id}/answer` also takes `"no_policy": true`. The request is saved with `outcome` `no_policy`, no attested document is created, and the gap becomes a process gap exactly as `POST /api/author/gaps/{gap_id}/no-source` does, with the expert's statement and signer as the reason.

### POST /api/author/gaps/{gap_id}/dismiss

Knowledge Ops author only. Explore only.

Body: `{ "world": "explore", "kind": "already_answered" | "out_of_scope", "reason": "...", "unit_id": "U-..." }`.

The reason needs at least four words. `already_answered` needs `unit_id` of an approved unit. The gap status becomes `dismissed` and it leaves the Knowledge Ops queue. No unit is written.

Errors: `Say why, in at least four words.` `Name the approved unit that already answers it.` `Choose why: already answered, or outside what Harbor does.`

### GET /api/author/drift

Knowledge Ops author only. Explore only.

Lists source changes routed to Knowledge Ops, plus the automatic cosmetic log. Legal's `GET /api/legal/drift` is unchanged and still lists the material change on Legal wording.

```json
{
  "items": [
    {
      "id": 1,
      "unit_id": "U-CB-HOURS",
      "old_wording": "Offer a Harbor callback window on weekdays from 8:00 a.m. to 5:00 p.m. Eastern. These hours are illustrative.",
      "new_wording": "Offer a Harbor callback window on weekdays from 8:00 a.m. to 6:00 p.m. Eastern. These hours are illustrative.",
      "queue": "Knowledge Ops",
      "status": "author"
    }
  ],
  "automatic": [
    {
      "id": 2,
      "unit_id": "U-CB-NOTE",
      "summary": "Cosmetic edit logged, nothing flagged.",
      "actor": "System",
      "automatic": true
    }
  ]
}
```

The approved wording stays live until Knowledge Ops accepts a fix.

### POST /api/author/drift/{id}

Knowledge Ops author only. Explore only.

Body: `{ "world": "explore", "action": "accept_fix", "reason": "", "text": "" }`.

`action` is `accept_fix`, `edit_and_accept`, or `keep_current`.

- `accept_fix` and `edit_and_accept` publish a new version and keep the old one in the history. `edit_and_accept` requires `text`. Without it the error is `Write the wording before accepting this fix.`
- `keep_current` needs a reason of at least four words. The unit is no longer stale, and the reason is recorded. A short reason returns `A reason of at least four words is required.`

```json
{ "ok": true, "message": "Recorded accept_fix on source change 1.", "id": 1, "action": "accept_fix" }
```

### GET /api/explore/insights

```json
{
  "open_gaps": 4,
  "drift_waiting": 0,
  "expired_count": 1,
  "tiles": [{ "key": "hit_at_1", "label": "hit@1", "display": "88%", "detail": "7 of 8" }],
  "score_counts": { "right_first": 7, "wrong": 0, "wrong_no_answers": 1, "scored": 8, "not_scored": 0 },
  "not_scored": 0,
  "held_out": { "pass": 2, "total": 3, "not_scored": 0 },
  "top_gaps": [{ "id": "c5", "cluster": "How long a Part D prior auth takes", "status": "proposed", "kind": "cluster", "search_count": 340, "findability": false }],
  "findability_gaps": [{ "id": "c0", "cluster": "Rx pricing disclaimer to read", "findability": true, "search_count": 160 }],
  "findability_count": 4,
  "process_gaps": [],
  "new_questions": { "count": 0, "examples": [] },
  "drift": { "material": false, "sent": false, "waiting": false, "summary": "" },
  "expired_units": [{ "unit_id": "U-RX-EDU-001-13" }],
  "feedback": { "week_start": "2026-11-02", "by_kind": [], "most_flagged": [] },
  "wrapups": { "count": 0, "verbatim_required": 0, "verbatim_confirmed": 0, "follow_ups": 0 },
  "acknowledgements": [],
  "message": "Illustrative, made-up data."
}
```

`process_gaps` lists questions sent back to the Knowledge owner because the business has no owner for the fact. The label on each is `The business has no answer yet`. `tiles` here are only `hit_at_1`, `over_abstain`, and `leaks`. The detail strings use the same golden set and the same `score_counts` as `GET /api/quality` after a score. `top_gaps` and `open_gaps` are content gaps. `findability_gaps` are the clusters marked `findability`, which are questions an approved unit already answers. This read does not mark the database as scored. `top_gaps` and `open_gaps` leave out the unclustered bucket. Every gap in `top_gaps` has `kind` `cluster`. `new_questions.count` is the number of distinct questions in that bucket, and `examples` holds up to five of them, already redacted. Out-of-scope member chat questions never reach the bucket. `wrapups` is the same summary as `GET /api/explore/wrapups`. `acknowledgements` lists each approved version above 1, with the advocate roles whose knowledge bases include that unit split into `acknowledged_by` and `pending`.

### POST /api/explore/wrapup

Body:

```json
{
  "world": "explore",
  "role": "Pharmacy advocate",
  "call_id": "drug-price",
  "call_reason": "Drug price question",
  "unit_ids": ["U-RX-EDU-001-09"],
  "read_verbatim": true,
  "outcome": "resolved",
  "note": ""
}
```

A Pharmacy advocate or an Insurance advocate records how the call ended. `outcome` is `resolved`, `follow_up`, or `transferred`. When any known id is an approved unit of type `verbatim`, `read_verbatim` must be `true` or `false`. Unknown unit ids are dropped. `call_id`, `call_reason`, and `note` are redacted before they are stored. A follow-up with a blank note is refused.

Send `displayed_units` as a list of `{ "unit_id", "version", "text" }`. `text` is the wording that was on screen. The stored record keeps `unit_id`, `version`, and `text_hash` (sha256 of that text). `superseded_read` is true when that version is no longer the approved one. If `displayed_units` is omitted, the server fills the live approved version for each known `unit_id`.

```json
{
  "ok": true,
  "message": "Wrap-up saved.",
  "wrapup": {
    "id": "W-1",
    "role": "Pharmacy advocate",
    "call_id": "drug-price",
    "call_reason": "Drug price question",
    "unit_ids": ["U-RX-EDU-001-09"],
    "displayed_units": [
      {
        "unit_id": "U-RX-EDU-001-09",
        "version": 1,
        "text_hash": "sha256 hex of the text that was on screen",
        "superseded_read": false
      }
    ],
    "read_verbatim": true,
    "outcome": "resolved",
    "note": "",
    "created_at": "2026-11-04T15:40:00-05:00"
  },
  "summary": { "count": 1, "verbatim_required": 1, "verbatim_confirmed": 1, "follow_ups": 0 },
  "undo": { "available": true, "label": "Wrap-up saved.", "world": "explore" },
  "illustrative": true
}
```

`summary.verbatim_required` counts wrap-ups whose `read_verbatim` is not null. `verbatim_confirmed` counts those stored as yes. The activity line is `Pharmacy advocate wrapped up a call about Drug price question. Read the approved wording word for word: yes.` False uses `no`. When `read_verbatim` is null that sentence is left out. A `follow_up` outcome appends ` Follow-up needed.`

Errors:

- `Only an advocate can wrap up a call.`
- `Choose how the call ended.`
- `Confirm whether you read the approved wording word for word.`
- `Add a note so the follow-up has what it needs.`

### GET /api/explore/wrapups

Query: `world` (default `explore`).

```json
{
  "summary": { "count": 1, "verbatim_required": 1, "verbatim_confirmed": 1, "follow_ups": 0 },
  "items": [
    {
      "id": "W-1",
      "role": "Pharmacy advocate",
      "call_id": "drug-price",
      "call_reason": "Drug price question",
      "unit_ids": ["U-RX-EDU-001-09"],
      "read_verbatim": true,
      "outcome": "resolved",
      "note": "",
      "created_at": "2026-11-04T15:40:00-05:00"
    }
  ]
}
```

`items` is newest first, at most 20. `summary` counts every wrap-up, including ones past that limit.

### GET /api/explore/changes

Query: `world` (default `explore`), `role` (required).

Approved units with `version` greater than 1 that this role can search, using the same knowledge-base overlap search uses. Newest version first.

```json
{
  "role": "Pharmacy advocate",
  "pending": 1,
  "changes": [
    {
      "unit_id": "U-RX-EDU-001-09",
      "title": "Pricing estimate disclaimer",
      "type": "verbatim",
      "version": 2,
      "previous_version": 1,
      "approved_on": "2026-11-04",
      "approved_by": "Legal approver",
      "text": "The price I quote is an estimate...",
      "previous_text": "The price I quote is an estimate...",
      "diff": [{ "kind": "equal", "text": "The price I quote is an estimate..." }],
      "acknowledged": false
    }
  ]
}
```

`title` drops a trailing `(Legal)` or `(Legal verbatim)`. `approved_on` is the calendar day on the unit. `diff` is the word diff from `previous_text` to `text` (`kind` is `equal`, `remove`, or `add`). `pending` counts changes with `acknowledged` false. An unknown role returns `Unknown role.`

### POST /api/explore/changes/acknowledge

Body: `{ "world": "explore", "role": "Pharmacy advocate", "unit_id": "U-RX-EDU-001-09", "version": 2 }`.

Only a Pharmacy advocate or an Insurance advocate. A missing unit version returns 404 `That unit version does not exist.` A second call for the same role, unit, and version returns 200 with the same message and does not add another activity line.

Activity line: `Pharmacy advocate acknowledged version 2 of Pricing estimate disclaimer.`

```json
{
  "ok": true,
  "message": "Acknowledged version 2 of Pricing estimate disclaimer.",
  "changes": {
    "role": "Pharmacy advocate",
    "pending": 0,
    "changes": [
      { "unit_id": "U-RX-EDU-001-09", "title": "Pricing estimate disclaimer", "version": 2, "acknowledged": true }
    ]
  },
  "undo": { "available": true, "label": "Acknowledged version 2 of Pricing estimate disclaimer.", "world": "explore" },
  "illustrative": true
}
```

`changes` has the same shape as `GET /api/explore/changes`. The item stays in the list with `acknowledged` true, and `pending` drops. A repeat does not take a new undo snapshot. Error for any other role: `Only an advocate can acknowledge a change.`

### GET /api/explore/scope

Query: `role` (required).

```json
{
  "role": "Pharmacy advocate",
  "knowledge_bases": ["pharmacy", "shared-legal"],
  "pages": ["Agent desktop", "What I can read"]
}
```

Error: `Unknown role.`

## Developer portal

These reads default to `world=explore`. Pass `world=guided` to read the demo database instead. They do not log searches and do not spend live calls.

### GET /api/portal/quick-start

```json
{
  "base": "/api/portal",
  "sample_request": "GET /api/portal/units/U-RX-EDU-001-09?channel=member_chat",
  "sample_unit": { "unit_id": "U-RX-EDU-001-09", "channel": "member_chat", "text": "These prices are estimates...", "citation": "Harbor Health, pricing estimate disclaimer, version 1" },
  "sample_event": { "event": "unit.revised", "unit_id": "U-RX-EDU-001-09", "version": 2, "previous_version": 1, "ts": "2026-11-04 10:15 ET" },
  "endpoints": [
    { "method": "GET", "path": "/api/portal/units/{unit_id}?channel=", "what": "One approved unit, with the text for that channel, version, and citation." },
    { "method": "GET", "path": "/api/portal/units?knowledge_base=&channel=", "what": "Approved units a channel may render." },
    { "method": "GET", "path": "/api/portal/answers?question=&role=", "what": "One cited unit, or an explicit no-answer." },
    { "method": "GET", "path": "/api/units/{unit_id}/as-of?timestamp=", "what": "The version that was live at a given time." },
    { "method": "GET", "path": "/api/portal/events", "what": "unit.revised, unit.retired, and unit.flagged events from this database." }
  ]
}
```

`sample_unit` is null when nothing is approved.

### GET /api/portal/units

Query: `world`, `knowledge_base`, `channel`. Approved, search-visible units. `knowledge_base` must appear in the unit's scope. `channel` is kept on the payload when you pass it. A channel filter that is not one of `member_chat`, `voice_bot`, `website`, or `advocate_guidance` still returns the unit and sets `text` from the advocate wording.

```json
{ "count": 40, "units": [{ "unit_id": "U-RX-EDU-001-09", "version": 1, "text": "The price I quote is an estimate...", "citation": "Harbor Health, pricing estimate disclaimer, version 1" }] }
```

### GET /api/portal/units/{unit_id}

Query: `world`, `channel`.

```json
{ "unit": { "unit_id": "U-RX-EDU-001-09", "version": 1, "channel": "voice_bot", "text": "These prices are estimates..." } }
```

An approved unit is returned by id even when `search_visible` is false, including `U-RX-EDU-PRICE-ANY`. The list route still returns only search-visible units. 404: `No approved unit U-NOPE.` `U-IVR-AUTH-001 is not approved for member_chat.`

### GET /api/portal/events

Query: `world`. Up to 20 events. `unit.revised` is an approved version greater than 1. `unit.retired` is a retired row. `unit.flagged` is a stale unit.

```json
{
  "events": [
    { "event": "unit.revised", "unit_id": "U-RX-EDU-001-09", "version": 2, "title": "Pricing estimate disclaimer (Legal)" },
    { "event": "unit.flagged", "unit_id": "U-RX-EDU-001-09", "version": 2, "title": "Pricing estimate disclaimer (Legal)" }
  ],
  "message": ""
}
```

Each publish and revision event includes `ts` and `previous_version`. The log is append-only. Undo adds `unit.retracted` or `action.reversed` and does not delete earlier events.

Empty message: `No change events yet. Publish a revision, resolve a conflict, or apply a drift edit.`

### POST /api/explore/verify

Body: `{ "member_id": "HBR-20418", "date_of_birth": "1951-03-14" }`. Records verification for that member in the session when the date of birth matches the plan file. Profile, member record, drug price, visit cost, and advocate ask then return figures. A mismatch returns 400 `Those identifiers do not match the plan record.`

### POST /api/explore/phone/authenticate

The same body. Required before `POST /api/explore/member` with `channel` `voice_bot` returns a member-specific price or visit cost.

In-session approvals add `approver_name` and `approval_method` (`single`, `bulk`, or `seed`) on the unit. `POST /api/legal/approve-all` and `POST /api/author/approve-all` return 400 in the explore world. Guided demo shortcuts stay available and are recorded as `bulk`.

### GET /api/portal/answers

Query: `question` (required), `role` (default `Pharmacy advocate`), `world` (default `explore`), `member_id` (required for Member). A Member request with no member id is 400 `A member is required.` An unknown `member_id` is 404. Portal answers are not tied to the Explore session role. A question with no saved answer returns `status` `cache_miss`, `abstained` false, and empty text. That is separate from an abstention. The portal does not place a live call. When the Insurance advocate asks `what do I say before I quote a cost` and the sandbox has no approving saved answer, the portal returns the published desktop unit `U-BEN-COST-001-02`.

Advocate role:

```json
{
  "ok": true,
  "role": "Pharmacy advocate",
  "abstained": false,
  "text": "The price I quote is an estimate...",
  "unit_id": "U-RX-EDU-001-09",
  "version": 1,
  "citation": "Pricing estimate disclaimer (Legal), version 1",
  "searched": ["pharmacy", "shared-legal"],
  "ai_source": "cached",
  "note": "Illustrative, made-up data"
}
```

Member role, when the question has no price, visit, referral, authorized-caller, complaint, or out-of-scope intent. No `unit_id`, no advocate text. `text` is the member wording only.

```json
{
  "ok": true,
  "role": "Member",
  "abstained": false,
  "text": "Specialty drugs stay at Harbor Specialty Pharmacy...",
  "citation": "Source: Harbor Health, specialty drugs stay at the specialty pharmacy, version 1",
  "ai_source": "cached",
  "note": "Illustrative, made-up data"
}
```

An abstention on that path sets `abstained: true`, `text` to an empty string, and `citation` to an empty string.

When the question matches a member-chat intent, the portal returns that same reply. `text` is the chat reply. `units` are member text with a citation. `price` or `visit_cost` is present when the chat reply has one. `illustrative` is true. `how much is my atorvastatin` is `kind` `price` and `price` `0` for `HBR-20418`.

```json
{
  "ok": true,
  "role": "Member",
  "kind": "price",
  "text": "Atorvastatin 20 mg, 30-day supply at a preferred pharmacy: $0.",
  "price": { "price": 0, "price_display": "$0", "pharmacy": "preferred_retail", "days": 30, "available": true },
  "units": [
    {
      "unit_id": "U-RX-EDU-001-09",
      "title": "Pricing estimate disclaimer",
      "text": "These prices are estimates...",
      "citation": "Source: Harbor Health, pricing estimate disclaimer, version 1"
    }
  ],
  "illustrative": true,
  "note": "Illustrative, made-up data"
}
```

Errors: `Enter a question.` `Unknown role.` `A member is required.` `Search has nothing to read yet. Legal must approve units first.`

## Contract added after pass 5

Every figure below is illustrative. New member and phone sentences are approved units with `search_visible` 0, so they are not in a guided candidate pool.

### Answer status and citations

Search, Explore ask, member chat, and portal answers include `status` or `answer_status`: `answer`, `abstain`, `clarify`, `out_of_scope`, `price`, `visit_cost`, `plan_figure`, `safety`, `handoff`, or `cache_miss`. The engine may still set `status` to `blocked_conflict` or `transfer` on a desktop search. `citations` is a list of `{unit_id, version, title, approved_by, approved_on}`. The older string `citation` remains. Citations are not joined into `text` or `reply`.

Server sentences that used to be written in the handler are approved templates: `U-TPL-PRICE-001`, `U-TPL-VISIT-001`, `U-TPL-REFERRAL-NOTE-001`, and `U-TPL-OOP-001`. The response cites them.

### POST /api/explore/open

Body: `{ "role" }`. Stores the canonical role on the session. 400 `Unknown role.` lists `allowed`.

### POST /api/demo/units/{unit_id}/tags

Body: `{ "world", "audience", "domain", "tags" }`. Records a human tag decision for that unit. Bulk confirm is unchanged. In guided, an audience edit that would change who can see the unit returns 400 `That audience change would change who can see this unit in the guided search pool. The explore sandbox can record it.` Tags do not change the guided candidate pool. Step 1 is done when every remaining version-1 unit is confirmed. `GET /api/demo/extraction` returns the edited tags, audience, and domain on that unit, with `tags_edited_by` set to `Knowledge Ops author`. An empty audience, domain, or tag list leaves that field as it was stored.

### POST /api/channels/publish

Optional `text` and `member_text`. When they are omitted, the prepared revision is published and step 8 holds. Empty text is 400 `Write the wording before publishing.` Unchanged text is rejected. Wording that is not the prepared revision and is not in the source is rejected. A typed revision sets `edited_by_legal` true and stores `approver_name`. The message is `Published version {n} to the advocate desktop, member chat, the website, and the phone line.` The Legal email names the same four channels. `saved_answers` says the prepared wording still matches saved answers, or that typed wording can miss a saved answer until a new one exists. The guided score stays on the frozen snapshot. An idempotency key returns the first response.

### GET /api/legal/workload

Query: `world`. Counts by type (`verbatim`, `policy`, `cost`, `other`) and by risk tier. Illustrative minutes are 20 high, 10 medium, and 5 low. `total_hours` is those minutes divided by 60. `proposed_tiering` says only verbatim, cost, and clinical units need Legal, and low-risk units go to Knowledge Ops batch review. `illustrative` is true.

### POST /api/legal/review/extend and POST /api/legal/review/retire

Legal only. Extend body: `{ "unit_id", "reason", "review_by" }`. Retire body: `{ "unit_id", "reason" }`. In Explore, a unit past `review_by` with no extension leaves search. The note is `This answer is past its review date and is waiting for Legal.` A queue item lets Legal extend the date or retire the unit. Guided keeps the seeded extension on `U-RX-EDU-001-13`, so the guided pool does not change.

### POST /api/legal/link-review/accept

Legal only. Body: `{ "unit_id" }`. `U-RX-EDU-PRICE-ANY` is linked to `U-RX-EDU-001-09`. Publishing a revision of either opens `A linked disclaimer may need the same change` for the other. Both versions stay approved until Legal accepts the review, which records no wording change. Each new version copies `sibling_of`. If the row it was copied from is blank, the link is read from any earlier version that still has it.

### GET /api/legal/link-reviews

Query: `world`. Lists reviews that are still open (`status` sent). Each item has `unit_id`, `sibling_id`, `label`, and `created_at`. After publishing version 2 of `U-RX-EDU-001-09` in Explore, the list includes `U-RX-EDU-PRICE-ANY`, sibling `U-RX-EDU-001-09`, and the label `A linked disclaimer may need the same change`. Accepting that review removes it from the list. A past-review item that is still waiting is listed too, with its own label.

### POST /api/explore/member and the phone line

`channel` `voice_bot` requires `call_id`. Authentication from `POST /api/explore/phone/authenticate` applies to that `call_id` only. A missing `call_id` is 400 `A call_id is required.` Member routes never default to `HBR-20418`. The body or query must include `member_id`, or the response is 400 `A member is required.`

`ivr_prompts` includes approved units:

| Key | Id | Text |
| --- | --- | --- |
| `greeting` | `U-IVR-GREETING-001` | Thank you for calling Harbor Health. In a few words, tell me what you are calling about. |
| `anything_else` | `U-IVR-ANYTHING-001` | Is there anything else? Press 0 to talk to a member advocate. |
| `no_answer` | `U-IVR-NOANSWER-001` | I don't have an approved answer for that yet. |
| `verified` | `U-IVR-VERIFIED-001` | You are verified for this call. |

The line can choose among Dana's drugs, a 90-day mail fill, a specialist cost, the out-of-pocket maximum, a billing problem, and a callback. Clarify chips are returned for the caller to pick.

### POST /api/explore/member/authorized-caller

Body: `{ "member_id", "caller_name", "relationship" }`. Status `pending`. The caller name is redacted in the activity log. The response includes a confirmation number that starts with `AC-`. The advocate record shows a recent contact `Asked to add an authorized caller`. The confirmation wording is `U-BEN-CALLER-CONFIRM-001`.

### GET /api/explore/member/glossary

Approved member definitions, grade 6 to 8, for tier (`U-GLOSS-TIER-001`), coverage stage (`U-GLOSS-STAGE-001`), deductible (`U-GLOSS-DEDUCT-001`), preferred retail pharmacy (`U-GLOSS-PREF-001`), mail order (`U-GLOSS-MAIL-001`), and out-of-pocket maximum (`U-GLOSS-OOP-001`). Chat returns the same units with `kind` `definition`.

### Member chat additions

A follow-up keeps the drug, the supply, and the pharmacy when it continues the same question (`cheaper`, mail, 90, yes, that one, preferred, retail). A new topic does not inherit the drug. A cheaper comparison returns both prices and the per-month difference. `how much will all my drugs cost this month` lists each drug and a monthly total, each figure with its disclaimer. Two questions in one message answer the first and offer the second as a chip. `I can't afford my medicine` returns `U-BEN-COST-HELP-001`, the unit's opener, and the advocate chip. Overcharge and higher-than-expected phrasings open the complaint chips. A specific reason chip returns `U-RX-OVER-ESTIMATE-001`, `U-RX-OVER-SUPPLY-001`, `U-RX-OVER-DEDUCT-001`, or `U-RX-OVER-LIST-001`. Dana's claims include an illustrative pharmacy claim of $140 for apixaban on 2026-10-18, so `See my recent claims` shows it. Also approved, and not in the search pool: `U-IVR-CALLBACK-001`, `U-BEN-GRIEVANCE-001`, and `U-BEN-OON-NEXT-001` (`Ask your primary care doctor for an in-network referral`).

`U-RX-EDU-PRICE-ANY` member text is the plain sentence for the supply and pharmacy shown. The advocate text is unchanged. The member text of `U-RX-EDU-001-09` is unchanged. That sentence is a member search candidate, and replacing it would change the saved answers, including the guided member candidates. The plain 30-day sentence is documented here and was not written onto that unit.

An out-of-network specialist cost cites `U-BEN-OON-RULE-001` and `U-BEN-OON-NEXT-001`. It does not cite the in-network referral unit.

### Who may mutate

The session role must match. Guided records the route's role as the presenter and does not return 403.

| Routes | Role | 403 detail |
| --- | --- | --- |
| Legal approve, decline, drift approve and return, publish, conflict resolution, review extend and retire, link-review accept | Legal approver | Only the Legal approver can do this. |
| Knowledge Ops approve and edit, gap draft and send, drift apply and send | Knowledge Ops author | Only the Knowledge Ops author can do this. |
| Gap decisions | Knowledge owner | Only the Knowledge owner can do this. |

Bulk approve-all in Explore still returns 400 that bulk approval is closed in the sandbox, before the role check.

### Events and webhooks

Each event has `event_id`, `occurred_at` (RFC 3339), `previous_version`, and `ts`. Events are append-only.

`GET /api/portal/events?cursor=` returns `next_cursor`. Page size is 20.

`POST /api/portal/webhooks` body `{ "url", "events" }` registers a subscriber on the session and returns a signing secret. Deliveries are recorded, not sent, with an HMAC-SHA256 signature and `attempts` 1.

### GET /api/portal/openapi.json

Describes the portal routes and the problem schema. Unknown `channel` on `GET /api/portal/units/{id}` is 400 and `allowed` lists `advocate_guidance`, `member_chat`, `voice_bot`, and `website`. A known channel the unit does not list stays 404.

### Website units

Fetch by id. Search does not show them.

| Id | Sentence |
| --- | --- |
| `U-SITE-MAIL-001` | Mail order fills 90-day supplies only. |
| `U-SITE-FIND-001` | To find a doctor, call 1-800-555-0148, 8 AM to 8 PM, seven days a week. The number and the hours are illustrative. |
| `U-SITE-HELP-001` | Call 1-800-555-0148, 8 AM to 8 PM, seven days a week, or ask in chat. A member advocate can take it from there. Hours are illustrative. |

### Explore retrieval

The saved-answer cache key folds case, punctuation, and whitespace. Explore retrieves the top 20 lexical candidates, with a spelling layer and brand synonyms (Eliquis and apixaban, Lipitor and atorvastatin, Glucophage and metformin). Saved answers were recorded for three candidates, so when the 20-candidate prompt has no saved answer the sandbox replays the top-3 saved answer and still returns the 20 ids. A live call would send 20. Guided retrieval stays at 3.

### Transfers

A pharmacy question about a referral or a cardiologist returns `transfer: { "queue": "Insurance queue", "reason" }` so the desktop can offer the transfer. The answer stays an abstention when no pharmacy unit answers it. A blocked foreign conflict still sets `transfer_to`.

### Cosmetic edits

An edit outside a verbatim span still logs `Cosmetic edit logged. Nothing was flagged.` Any edit inside a verbatim span, including a comma, creates a Legal item labelled `Cosmetic change inside Legal wording`. The approved version stays live. Legal can accept it as no change or return it. If the guided cosmetic edit is inside the span, step 7 shows it as sent to Legal. Step 8 does not change. The web screen still prefixes its own cosmetic line. The API message for that comma is `Sent to Legal: a comma inside Legal wording. The approved version stays live.`
