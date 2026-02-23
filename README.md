# Sentinel-Ops

Sentinel-Ops is an interview-grade Intelligence Collection Operating System for high-velocity blockchain investigations. It transforms distributed contractor submissions into validated, auditable, export-ready datasets under 72-hour case deadlines.

## Why This Matters

Investigations fail when collection quality collapses under pressure: duplicate addresses, conflicting labels, weak provenance, and delayed analyst handoff. Sentinel-Ops addresses this with strict schemas, deterministic validation, append-only events, conflict arbitration, and manager-driven decisions.

## What It Demonstrates

- Event-driven architecture with derived state (no destructive updates)
- Deterministic validation and hashing for defensibility
- Human-in-the-loop review workflow with triage priority
- Contractor performance visibility (acceptance/conflict/review burden)
- Clean JSON/CSV export of approved intelligence with provenance

## Architecture (High-level)

```text
Contractors
  -> FastAPI Submission Gateway
  -> Validation + Dedupe + Conflict Detection
  -> Append-only Submission Event Ledger
  -> Scoring / Triage
  -> Streamlit Operations Dashboard
  -> Manager Actions
  -> Approved Export (JSON / CSV)
```

## Quickstart

```bash
make install
make init-db
make seed
```

Start API:

```bash
make dev-api
```

Start dashboard (new terminal):

```bash
make dev-ui
```

Run quality checks:

```bash
make lint
make test
```

## Core API Endpoints

- `POST /cases`
- `GET /cases`
- `GET /contractors`
- `POST /cases/{case_id}/submit`
- `GET /cases/{case_id}/submissions`
- `GET /submissions/{id}`
- `POST /submissions/{id}/actions`
- `GET /cases/{case_id}/export?format=json|csv`

## Demo Dataset

`make seed` creates a deterministic demo dataset (fresh DB):

- 1 case (`HIGH`, 72-hour deadline)
- 50 contractors
- 2000 submissions
- controlled duplicates and conflicts

## Repo Layout

- `/Users/rhys/Desktop/Sentinal Ops/app` FastAPI app and routes
- `/Users/rhys/Desktop/Sentinal Ops/sentinel` core logic (schemas, validation, scoring, events)
- `/Users/rhys/Desktop/Sentinal Ops/dashboard` Streamlit command center
- `/Users/rhys/Desktop/Sentinal Ops/scripts` init + seed scripts
- `/Users/rhys/Desktop/Sentinal Ops/migrations` Alembic migrations
- `/Users/rhys/Desktop/Sentinal Ops/tests` pytest suite
- `/Users/rhys/Desktop/Sentinal Ops/docs` architecture and operating docs

## Notes

- SQLite is default for local execution and interview portability.
- Migrations are managed by Alembic (`make init-db`).
- Event history is append-only; current state is derived from latest events.
