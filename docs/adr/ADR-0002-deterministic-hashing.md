# ADR-0002: Deterministic Hashing via Canonical JSON

## Context

Sentinel-Ops needs reproducible integrity identifiers for submissions so investigators can verify payload equivalence and avoid ambiguous duplicate handling.

Non-canonical serialization can produce different hashes for semantically equivalent payloads due to key order and formatting differences.

## Decision

Compute `submission_hash` from canonical JSON and SHA-256.

- Canonicalization uses stable key ordering and normalized separators.
- Hash input includes case context and normalized submission payload fields.
- Equivalent payloads produce identical hashes regardless of input key order.

## Alternatives Considered

1. Hash raw request body
- Sensitive to client formatting and key order; not reproducible across systems.

2. Use random UUID only
- Unique identity but no deterministic payload integrity signal.

3. Use database-generated checksum post-insert
- Harder to reason about client-visible determinism and replay parity.

## Consequences

Positive:
- Defensible reproducibility for audits and verification tests.
- Strong basis for dedupe and integrity workflows.

Trade-offs:
- Requires strict canonicalization discipline across code paths.
- Any schema evolution requires careful hash-input versioning strategy.
