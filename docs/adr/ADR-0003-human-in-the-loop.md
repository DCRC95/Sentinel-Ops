# ADR-0003: Human-in-the-Loop Arbitration over Full Automation

## Context

Blockchain intelligence submissions include ambiguity, conflicting attributions, and incomplete evidence. Fully automated acceptance/rejection risks overconfidence and brittle false certainty under operational pressure.

Sentinel-Ops is intended for 72-hour investigations where triage speed matters, but analyst judgment remains critical for disputed signals.

## Decision

Adopt a human-in-the-loop model:

- Automation handles schema checks, validation, dedupe, conflict flagging, and triage scoring.
- Managers/analysts make disposition decisions (`APPROVED`, `REJECTED`, `ESCALATED`, `REQUEST_MORE_EVIDENCE`).
- Decisions are recorded as append-only events for accountability.

## Alternatives Considered

1. Fully automated decisioning
- Faster throughput but poor explainability and high error risk in ambiguous cases.

2. Fully manual review of all submissions
- Better control but fails operational speed and scale requirements.

3. Confidence-threshold auto-approval with exceptions
- Partial compromise, but still risky without mature calibration and robust feedback loops.

## Consequences

Positive:
- Preserves analyst authority where ambiguity is highest.
- Improves defensibility and trust with explicit decision provenance.
- Keeps automation focused on reducing noise, not replacing judgment.

Trade-offs:
- Some review backlog persists by design.
- Requires clear queue prioritization and manager UX to stay performant.
