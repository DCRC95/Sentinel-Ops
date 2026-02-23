from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    INGESTED = "INGESTED"
    VALIDATED = "VALIDATED"
    CONFLICTED = "CONFLICTED"
    ENRICHED = "ENRICHED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    EXPORTED = "EXPORTED"
    AI_AUDITED = "AI_AUDITED"


ALL_EVENT_TYPES = {event.value for event in EventType}
