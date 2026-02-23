# Validation Engine

## Purpose

Automatically filter invalid or low-quality submissions before analyst review.

## Validation Stages

### Structural
- address format check
- chain normalization
- required fields

### Logical
- duplicate detection
- conflict identification

## Output

Produces VALIDATED event containing:

- pass/fail
- normalized values
- duplicate references
- conflict references
- validation reasons

## Determinism Requirement

Given identical input payloads, validation output must be identical.
