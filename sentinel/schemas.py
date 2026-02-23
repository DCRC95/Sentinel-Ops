from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class PriorityEnum(StrEnum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class CaseStatusEnum(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ChainEnum(StrEnum):
    ETH = "ETH"
    BTC = "BTC"
    SOL = "SOL"


class ScamTypeEnum(StrEnum):
    PHISHING = "Phishing"
    PIG_BUTCHERING = "PigButchering"
    RUGPULL = "Rugpull"
    EXCHANGE = "Exchange"
    OTHER = "Other"


class ManagerActionEnum(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


class CreateCaseRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    priority: PriorityEnum = PriorityEnum.MED
    start_time: datetime | None = None
    deadline_time: datetime | None = None

    @field_validator("start_time", "deadline_time")
    @classmethod
    def ensure_tz(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class CaseResponse(BaseModel):
    case_id: UUID
    title: str
    priority: PriorityEnum
    start_time: datetime
    deadline_time: datetime
    status: CaseStatusEnum


class ContractorResponse(BaseModel):
    contractor_id: UUID
    handle: str
    created_at: datetime


class SubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    contractor_id: UUID
    chain: ChainEnum = Field(alias="blockchain")
    address: str = Field(min_length=2, max_length=256)
    scam_type: ScamTypeEnum
    source_url: HttpUrl
    confidence_score: int = Field(ge=1, le=5)
    evidence_type: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=4000)


class ValidationResult(BaseModel):
    passed: bool
    reasons: list[str]
    normalized_chain: str
    normalized_address: str
    duplicate_of: list[str]
    conflict_with: list[str]


class SubmitResponse(BaseModel):
    submission_id: UUID
    submission_hash: str
    validation: ValidationResult


class ManagerActionRequest(BaseModel):
    action: ManagerActionEnum
    actor: str = "manager"
    notes: str | None = None


class SubmissionListItem(BaseModel):
    submission_id: UUID
    case_id: UUID
    contractor_id: UUID
    chain: str
    address: str
    scam_type: str
    source_url: str
    confidence_score: int
    created_at: datetime
    submission_hash: str
    latest_event_type: str
    is_duplicate: bool
    is_conflicted: bool
    triage_priority: float


class SubmissionEventResponse(BaseModel):
    event_id: UUID
    event_type: str
    event_payload_json: dict[str, Any]
    created_at: datetime
    actor: str


class SubmissionDetail(BaseModel):
    item: SubmissionListItem
    events: list[SubmissionEventResponse]


class ExportRecord(BaseModel):
    case_id: UUID
    submission_id: UUID
    contractor_id: UUID
    created_at: datetime
    chain: str
    address: str
    scam_type: str
    source_url: str
    confidence_score: int
    submission_hash: str
    validation_summary: dict[str, Any]


def derive_case_times(
    start_time: datetime | None,
    deadline_time: datetime | None,
) -> tuple[datetime, datetime]:
    start = start_time or datetime.now(UTC)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    deadline = deadline_time or (start + timedelta(hours=72))
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return start, deadline
