# Scoring Model

## Goal

Prioritize analyst attention rather than predict truth.

## Metrics

### Consensus Score
Agreement between contractors.

### Contractor Reliability
accepted / (accepted + rejected)

### Confidence Score
Submitted confidence normalized to 0–1.

## Composite Priority

priority =
0.4 contractor_reliability +
0.3 consensus_score +
0.3 confidence_score

## Design Rationale

Explainable scoring improves analyst trust and auditability.
