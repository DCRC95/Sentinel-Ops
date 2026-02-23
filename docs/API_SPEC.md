# API Specification

## POST /cases
Create investigation case.

## GET /cases
List cases.

## GET /contractors
List contractors.

## POST /cases/{case_id}/submit
Submit intelligence record.
System appends events:
- INGESTED
- VALIDATED
- EVIDENCE_ANALYZED
- CONFLICTED (when applicable)

## GET /cases/{case_id}/submissions
List submissions with derived state.

## GET /submissions/{id}
Get submission detail with full event trail.

## POST /submissions/{id}/actions
Manager actions:
- approve
- reject
- escalate
- request_more_evidence

## GET /cases/{case_id}/export
Export approved intelligence dataset (`format=json|csv`).
