# Intelligence Layer

## Purpose

The Intelligence Layer adds deterministic, evidence-aware signal generation on top of validated submissions. Its first engine is the Evidence Consistency Analyzer (ECA), which evaluates whether linked evidence text supports the submitted claim.

## Rule Philosophy

Sprint 3 uses deterministic rules before AI:

- reproducible outputs
- explainable scores
- easier verification and regression testing

This protects auditability while building analytical capability.

## Why Rules Before AI

Rules provide a stable foundation for investigative workflows:

- predictable behavior under scrutiny
- lower operational risk
- clear failure modes

AI augmentation can be layered later once inputs and guarantees are proven.

## Analyst Workflow Integration

Submission path now includes `EVIDENCE_ANALYZED` events:

`INGESTED -> VALIDATED -> EVIDENCE_ANALYZED -> (CONFLICTED?) -> APPROVED/REJECTED`

Managers review:

- evidence score
- address mention result
- classification support result
- analyzer notes

The manager still decides final disposition.

## Evidence Scoring (Phase 1)

Signals:

- address mention check
- classification keyword match
- source reachable check

Score:

`0.5 * address_match + 0.3 * keyword_match + 0.2 * source_reachable`

Range: `0.0–1.0`

## Limitations

- HTML extraction is basic and may miss dynamic content.
- Keyword rules are intentionally shallow and domain-limited.
- Score is triage guidance, not proof of truth.
- External source availability may vary; failures are handled safely.
