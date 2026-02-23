# Changelog

All notable changes to Sentinel-Ops will be documented here.

## [0.2.0] - 2026-02-23

### Added
- System invariant enforcement tests (`tests/test_invariants.py`)
- Event replay engine and replay verification test (`sentinel/replay.py`, `tests/test_event_replay.py`)
- Stress simulation framework and report generation (`scripts/simulate_failure.py`, `docs/STRESS_TEST.md`)
- Architecture Decision Records (`docs/adr/ADR-0001-event-sourcing.md`, `docs/adr/ADR-0002-deterministic-hashing.md`, `docs/adr/ADR-0003-human-in-the-loop.md`)

## [0.1.0] - Initial Architecture

### Added
- System architecture
- Event sourcing model
- Validation engine design
- Operations dashboard specification
