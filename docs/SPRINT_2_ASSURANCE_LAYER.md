# Sentinel-Ops — Sprint 2
## Assurance & System Integrity

- **Sprint Name:** Assurance Layer
- **Duration:** 5–7 days (focused execution)
- **Objective:** Prove Sentinel-Ops correctness, auditability, and operational resilience under scrutiny.

## 1. Sprint Goal

Establish formal guarantees that:

- event history cannot produce invalid states
- derived system state is mathematically reconstructible
- system behavior remains stable under stress conditions
- architectural decisions are explicitly justified

Deliverable outcome:

Sentinel-Ops becomes defensible as an intelligence-grade system.

## 2. Success Criteria (Definition of Done)

Sprint is complete only if:

- `make test` includes invariant validation tests
- event replay reconstructs system state exactly
- stress simulation runs successfully
- ADR documentation exists
- verification report updated
- changelog updated

## 3. Sprint Workstreams

### WORKSTREAM A — System Invariants

#### Purpose

Define rules that must never be violated regardless of code changes.

You are encoding system truth.

#### Tasks

Create:

`tests/test_invariants.py`

#### Required Invariants

**Invariant 1 — Validation Required**

A submission cannot be approved unless validated.

- `INGESTED → APPROVED` ❌
- `INGESTED → VALIDATED → APPROVED` ✅

Test:

- attempt approval without validation
- assert rejection or invalid state

**Invariant 2 — Export Requires Approval**

`EXPORTED` must follow `APPROVED`

Test:

- export non-approved submission
- assert failure

**Invariant 3 — Single Latest State**

A submission must never have multiple terminal states.

Test:

- ensure derived status equals latest event chronologically.

**Invariant 4 — Event Immutability**

Past events must never change.

Test:

- record event snapshot
- perform actions
- verify original event unchanged

**Invariant 5 — Conflict Logic Consistency**

Conflict events must reference valid submissions.

#### Deliverable

`pytest tests/test_invariants.py`

Expected outcome:

All invariants enforced by automated tests.

### WORKSTREAM B — Event Replay Verification

#### Purpose

Prove auditability mathematically.

If events are the source of truth, replaying them must rebuild state exactly.

#### Tasks

Create:

`sentinel/replay.py`

Function:

```python
def reconstruct_submission_state(events: list[Event]) -> SubmissionState:
    ...
```

Logic:

- sort events by timestamp
- apply transitions sequentially
- compute final state

Test

Create:

`tests/test_event_replay.py`

Steps:

- create submission
- apply actions (`validate → approve → export`)
- reconstruct state from events
- compare with API response

Assertion:

`reconstructed_state == api_state`

#### Deliverable

Proof that:

Event history alone reconstructs truth.

### WORKSTREAM C — Stress Simulation

#### Purpose

Demonstrate operational robustness.

This is a portfolio differentiator.

#### Tasks

Create:

`scripts/simulate_failure.py`

Simulate:

**Scenario 1 — Submission Burst**

5,000 rapid submissions

Measure:

- validation success rate
- processing latency

**Scenario 2 — Conflict Storm**

many contractors classify same address differently

Measure:

- conflict detection accuracy

**Scenario 3 — Invalid Payload Flood**

malformed submissions

Measure:

- rejection stability
- system crash resistance

Output

Generate:

`docs/STRESS_TEST.md`

Include:

- test scenarios
- metrics observed
- conclusions

### WORKSTREAM D — Architecture Decision Records (ADR)

#### Purpose

Make architectural reasoning explicit.

Create directory:

`docs/adr/`

**ADR-0001 — Event Sourcing**

Explain:

- why append-only chosen
- alternatives (CRUD state)
- consequences

**ADR-0002 — Deterministic Hashing**

Explain:

- canonical JSON
- reproducibility need
- audit implications

**ADR-0003 — Human-in-the-Loop Design**

Explain:

- automation limits
- analyst arbitration necessity

Format:

- Context
- Decision
- Alternatives
- Consequences

### WORKSTREAM E — Verification Update

Arbiter agent must update:

`docs/VERIFICATION_REPORT.md`

Add section:

`Sprint 2 Assurance Verification`

Include:

- invariant results
- replay validation results
- stress outcomes
- risk assessment

### WORKSTREAM F — Documentation + Versioning

Update:

`CHANGELOG.md`

Add:

```md
## [0.2.0] - Assurance Layer
### Added
- System invariant enforcement
- Event replay verification
- Stress simulation framework
- Architecture Decision Records
```

## 4. Execution Order (IMPORTANT)

Engineer agent executes:

1. invariants tests
2. replay engine
3. replay tests
4. stress simulation
5. ADR docs
6. changelog

Arbiter executes:

1. verification pass
2. report update

## 5. Acceptance Demo (New)

You must now be able to demonstrate:

- Show submission audit trail
- Reconstruct state from events
- Run stress simulation
- Show invariant tests protecting system

This moves demo from product → platform.

## 6. Expected Repository Evolution

After Sprint 2 your repo communicates:

Before:

“I built a system.”

After:

“I built a system that proves its own correctness.”

That distinction is enormous in senior engineering evaluation.
