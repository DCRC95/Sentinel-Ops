# Data Model

## Entities

### Contractor
Represents an intelligence contributor.

Fields:
- contractor_id (UUID)
- handle
- created_at

---

### Case
Represents an investigation window.

Fields:
- case_id
- title
- priority
- start_time
- deadline_time
- status

---

### Submission
Immutable intelligence claim.

Fields:
- submission_id
- contractor_id
- case_id
- chain
- address
- scam_type
- source_url
- confidence_score
- raw_payload_json
- submission_hash

NOTE:
Submissions are never updated.

---

### Submission Events
Tracks lifecycle transitions.

Fields:
- event_id
- submission_id
- event_type
- event_payload_json
- actor
- created_at
