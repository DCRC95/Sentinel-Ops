from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sentinel.events import EventType


@dataclass(frozen=True)
class ReplayEvent:
    event_type: str
    created_at: datetime
    event_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubmissionState:
    latest_event_type: str
    validated: bool
    approved: bool
    rejected: bool
    conflicted: bool
    exported: bool
    escalated: bool
    needs_more_evidence: bool
    duplicate_of: list[str]
    conflict_with: list[str]


def _to_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def reconstruct_submission_state(events: list[ReplayEvent]) -> SubmissionState:
    if not events:
        raise ValueError("cannot reconstruct state from empty event stream")

    ordered = sorted(events, key=lambda event: _to_datetime(event.created_at))

    validated = False
    approved = False
    rejected = False
    conflicted = False
    exported = False
    escalated = False
    needs_more_evidence = False
    duplicate_of: list[str] = []
    conflict_with: list[str] = []

    for event in ordered:
        event_type = event.event_type
        payload = event.event_payload or {}

        if event_type == EventType.VALIDATED.value:
            validated = bool(payload.get("passed", True))
            duplicate_of = list(payload.get("duplicate_of", []))
            conflict_with = list(payload.get("conflict_with", []))
        elif event_type == EventType.CONFLICTED.value:
            conflicted = True
            conflict_with = list(payload.get("conflict_with", conflict_with))
        elif event_type == EventType.APPROVED.value:
            approved = True
            rejected = False
        elif event_type == EventType.REJECTED.value:
            rejected = True
            approved = False
        elif event_type == EventType.EXPORTED.value:
            exported = True
        elif event_type == EventType.ESCALATED.value:
            escalated = True
        elif event_type == EventType.REQUEST_MORE_EVIDENCE.value:
            needs_more_evidence = True

    latest_event_type = ordered[-1].event_type
    return SubmissionState(
        latest_event_type=latest_event_type,
        validated=validated,
        approved=approved,
        rejected=rejected,
        conflicted=conflicted,
        exported=exported,
        escalated=escalated,
        needs_more_evidence=needs_more_evidence,
        duplicate_of=duplicate_of,
        conflict_with=conflict_with,
    )
