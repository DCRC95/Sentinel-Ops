# Sentinel-Ops

Sentinel-Ops is an intelligence collection operating system for high-velocity blockchain investigations. It helps teams coordinate distributed contractors, enforce deterministic validation, preserve chain-of-custody via append-only events, and export clean investigation-ready datasets under 72-hour deadlines.

## Why it matters

Spreadsheet-driven collection breaks under load: duplicate addresses, conflicting labels, low auditability, and unclear contributor quality. Sentinel-Ops replaces that with strict schemas, reproducible validation, and manager review workflows.

## Quickstart

```bash
make install
make init-db
make dev-api
# in another terminal
make dev-ui
```

## Architecture

```text
Contractors
  -> FastAPI Submission Gateway
  -> Deterministic Validation Engine
  -> Conflict + Duplicate Detection
  -> Append-only Event Ledger
  -> Review + Manager Actions
  -> Approved Export (CSV/JSON)
```

## Current status

- Phase 1: scaffold, DB models, app entrypoint, tooling
- Phase 2: ingestion, validation, events, derived listing, manager actions, export
