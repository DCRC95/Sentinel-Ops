# 3-Minute Demo Script

## Objective

Demonstrate an end-to-end 72-hour intelligence operations workflow:
- deterministic ingestion + validation
- conflict arbitration
- append-only provenance
- manager decisions
- approved-only export
- contractor performance visibility

## Pre-Demo Setup (60 seconds)

```bash
make install
make init-db
make seed
make dev-api
# new terminal
make dev-ui
```

Open dashboard in browser.

## Live Demo Flow (2 minutes)

1. **Case Overview**
- Select seeded case.
- Highlight deadline countdown and throughput/hour.
- Note pending review and pass rate.

2. **Conflict-First Review Queue**
- Sort order surfaces conflicted submissions first.
- Open one submission and show event history (`INGESTED -> VALIDATED -> CONFLICTED`).

3. **Manager Decisions**
- Approve several submissions, reject a few, escalate one.
- Refresh demonstrates latest derived status changes via newly appended events.

4. **Audit Trail**
- Open submission detail and show immutable event timeline.
- Emphasize no row mutation, only new events.

5. **Export**
- Run JSON export.
- Show only approved records are included, with validation summary + provenance fields.
- Run CSV export and download.

6. **Leaderboard**
- Show acceptance rate, conflict rate, and review burden by contractor.
- Explain how this helps prioritize contributors and manager attention.

## Key Talking Points

- Determinism: same input yields same validation + hash outputs.
- Defensibility: append-only provenance supports chain-of-custody.
- Human-in-loop: system automates noise, managers arbitrate ambiguity.
- Operational fit: optimized for high-volume, short-deadline investigations.
