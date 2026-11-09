# Cached model outputs

`fixtures/ai/` holds one JSON file per model call. The file name is `<task>-<sha256 prefix>.json`. Replay looks up a call by task and the full `input_sha256` of the user message. A file is written by `scripts/generate_fixtures.py` and is not edited afterward.

## Original fixtures

Calls saved before provenance was recorded have these fields:

- `task`
- `model`
- `generated_at` (America/New_York)
- `input_sha256`
- `input_ref`
- `output`

## New fixtures

Every new model call also stores:

- `response_id`: the API `response.id`
- `stop_reason`
- `usage`: `input_tokens` and `output_tokens`
- `prompt_sha256`: a hash of the system prompt and the JSON schema

Existing files are not backfilled. Both shapes are valid. Replay reads `output` from either shape.
