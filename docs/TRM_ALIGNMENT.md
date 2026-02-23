# Alignment with Intelligence Operations

Sentinel-Ops models real investigation workflows.

## 72-Hour Investigation Fit

- **Hour 0-6 (Collection):** contractors submit labeled addresses through strict schemas.
- **Hour 6-24 (Verification):** deterministic validation filters malformed, duplicate, and conflicting inputs.
- **Hour 24-48 (Arbitration):** managers focus on conflicts and high-priority queue items first.
- **Hour 48-72 (Dissemination):** approved, provenance-linked dataset is exported for downstream analysis.

## Operational Problems Addressed

- inconsistent contractor output
- manual validation bottlenecks
- lack of provenance tracking
- delayed analysis readiness

## Outcomes

- reduces collection-to-analysis lag
- enables 72-hour investigation cycles
- scales contributor networks safely
- improves intelligence defensibility

## Contractor Ops Mapping

- **Submission quality control:** schema + validation reduce garbage intake.
- **Disagreement management:** explicit `CONFLICTED` state and arbitration workflow.
- **Performance visibility:** leaderboard metrics expose acceptance/conflict/review burden trends.
- **Defensible handoff:** append-only event history preserves chain-of-custody for each record.
