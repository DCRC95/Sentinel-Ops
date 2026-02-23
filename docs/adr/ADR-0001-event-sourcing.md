# ADR-0001: Event Sourcing for Submission Lifecycle

## Context

Sentinel-Ops must support intelligence-grade auditability, chain-of-custody reconstruction, and defensible post-hoc review of decisions made under time pressure.

A mutable "current status" model makes it difficult to explain exactly how a submission moved from ingestion to approval/rejection/export, especially when multiple analysts or automated checks are involved.

## Decision

Use an append-only event model for submission lifecycle transitions.

- `submissions` remain immutable claim records.
- `submission_events` records every transition (`INGESTED`, `VALIDATED`, `CONFLICTED`, `APPROVED`, `REJECTED`, `EXPORTED`, etc.).
- Current state is derived from chronological event history, not in-place mutation.

## Alternatives Considered

1. CRUD status column on submissions
- Simple to query, but loses transition history unless additional audit tables are added.

2. Hybrid model (mutable status + partial audit log)
- Better than pure CRUD, but still creates dual sources of truth and synchronization risk.

3. External event store
- Strong event semantics but unnecessary operational complexity for current scope.

## Consequences

Positive:
- Full provenance and replayability.
- Deterministic derived-state checks become testable.
- Easier forensic and compliance narratives.

Trade-offs:
- Query patterns are more complex than simple status columns.
- Requires explicit replay/derivation logic and invariant tests.
