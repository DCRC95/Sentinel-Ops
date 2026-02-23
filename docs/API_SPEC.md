# API Specification

## POST /cases
Create investigation case.

## POST /cases/{case_id}/submit
Submit intelligence record.

## GET /cases/{case_id}/submissions
List submissions with derived state.

## POST /submissions/{id}/actions
Manager actions:
- approve
- reject
- escalate
- request_more_evidence

## GET /cases/{case_id}/export
Export approved intelligence dataset.
