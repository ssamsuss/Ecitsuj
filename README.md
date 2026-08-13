# Ecitsuj

Minimum viable product for simulating juror deliberation.

## Setup

Install the pinned dependencies and set `DATABASE_URL` to a PostgreSQL database:

```bash
python -m pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mockjury
```

Apply the versioned schema before starting the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Create a case with `POST /cases`. Requests are validated against the Pydantic case-packet model, whose contract is also published at `Schema/jsonschemas/case_packet.schema.json`. LLM vote and deliberation responses are validated before they are written to PostgreSQL.

## Reliability and cost

- **Retries**: `LLMClient` retries `LLMTransientError` failures with exponential backoff (`LLM_MAX_RETRIES`, default 3). Non-transient errors (validation, programming errors) are never retried.
- **Timeouts**: each LLM call is bounded by `LLM_TIMEOUT_SECONDS` (default 30); the whole run is bounded by `RUN_TIMEOUT_SECONDS` (default 300, overridable per request via `timeout_seconds` in `POST /runs`). Exceeding either marks the run `failed` instead of hanging.
- **Cost tracking**: `LLMClient` counts prompt/completion characters per call; `app/services/cost.py` estimates USD cost per model (rough, character-based) and persists it on `SimulationRun.estimated_cost_usd`, surfaced in `GET /runs/{run_id}`, the report metrics, and the JSON export.

## Evaluation and fairness harness

`eval/harness.py` validates the golden case packets under `case_packet/golden/` against both the Pydantic model and `case_packet.schema.json`, and — when `DATABASE_URL` is set — runs each case through a full simulation across 3 seeds plus a same-seed determinism re-run:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mockjury
python -m eval.harness
```

`eval/fairness.py` probes for bias by injecting different demographic-coded defendant names into otherwise-identical case facts and flagging any disparity in verdicts or confidence:

```bash
python -m eval.fairness
```

## Demo

`scripts/demo.py` ingests a golden case, runs a simulation, and prints a summary (splits, metrics, warnings, estimated cost):

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mockjury
python scripts/demo.py --case burglary_basic --juror-count 5 --max-rounds 2 --output run.json
```
