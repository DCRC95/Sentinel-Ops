# Event Model

## Philosophy

Sentinel-Ops uses event sourcing.

A submission does not change state.
Instead, new events describe its evolution.

## Event Types

- INGESTED
- VALIDATED
- CONFLICTED
- ENRICHED
- APPROVED
- REJECTED
- ESCALATED
- REQUEST_MORE_EVIDENCE
- EXPORTED

## State Derivation

Current state is computed as:

latest_event(submission_id)

## Benefits

- Full audit trail
- Reproducibility
- Analyst accountability
- Regulatory defensibility
