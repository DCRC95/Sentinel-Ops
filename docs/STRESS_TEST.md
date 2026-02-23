# Stress Test Report

Generated: 2026-02-23T17:09:32.845692+00:00

## Scenarios

### 1) Submission Burst

- Requests: 5000
- Validation success rate: 1.0000
- Average latency (ms): 21.26

### 2) Conflict Storm

- Requests: 400
- Detected conflicts: 399
- Expected conflicts: 399
- Conflict detection accuracy: 1.0000
- Average latency (ms): 41.55

### 3) Invalid Payload Flood

- Requests: 1000
- Rejection stability: 1.0000
- Crash resistance: stable
- Average latency (ms): 0.53

## Conclusions

- The system remained responsive under burst traffic and malformed payload pressure.
- Conflict detection remained accurate under high disagreement on a single address.
- Validation rejection path remained stable without process crashes.
