from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from sentinel.db import DB_PATH, get_db_session
from sentinel.events import EventType
from sentinel.hashing import canonical_json, submission_hash
from sentinel.models import Case, Contractor, Submission, SubmissionEvent
from sentinel.schemas import (
    CaseResponse,
    CreateCaseRequest,
    ExportRecord,
    ManagerActionRequest,
    SubmissionDetail,
    SubmissionEventResponse,
    SubmissionListItem,
    SubmitRequest,
    SubmitResponse,
    ValidationResult,
    derive_case_times,
)
from sentinel.scoring import (
    compute_consensus_score,
    compute_contractor_reliability,
    compute_triage_priority,
)
from sentinel.validation import validate_submission

app = FastAPI(title="Sentinel-Ops API", version="0.2.0")


ACTION_TO_EVENT = {
    "approve": EventType.APPROVED.value,
    "reject": EventType.REJECTED.value,
    "escalate": EventType.ESCALATED.value,
    "request_more_evidence": EventType.REQUEST_MORE_EVIDENCE.value,
}


@app.on_event("startup")
def startup() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _create_event(
    db: Session,
    *,
    submission_id: str,
    event_type: str,
    payload: dict[str, Any],
    actor: str,
) -> SubmissionEvent:
    event = SubmissionEvent(
        submission_id=submission_id,
        event_type=event_type,
        event_payload_json=canonical_json(payload),
        actor=actor,
    )
    db.add(event)
    return event


def _get_latest_event_type(db: Session, submission_id: str) -> str:
    latest = db.scalar(
        select(SubmissionEvent.event_type)
        .where(SubmissionEvent.submission_id == submission_id)
        .order_by(desc(SubmissionEvent.created_at))
        .limit(1)
    )
    return latest or "INGESTED"


def _latest_validated_payload(db: Session, submission_id: str) -> dict[str, Any]:
    event = db.scalar(
        select(SubmissionEvent)
        .where(
            SubmissionEvent.submission_id == submission_id,
            SubmissionEvent.event_type == "VALIDATED",
        )
        .order_by(desc(SubmissionEvent.created_at))
        .limit(1)
    )
    if event is None:
        return {}
    return json.loads(event.event_payload_json)


def _latest_event_type_map_for_case(db: Session, case_id: str) -> dict[str, str]:
    latest_events = db.execute(
        select(SubmissionEvent.submission_id, SubmissionEvent.event_type)
        .join(Submission, Submission.submission_id == SubmissionEvent.submission_id)
        .where(Submission.case_id == case_id)
        .order_by(SubmissionEvent.submission_id, desc(SubmissionEvent.created_at))
    ).all()

    latest_by_submission: dict[str, str] = {}
    for submission_id, event_type in latest_events:
        if submission_id not in latest_by_submission:
            latest_by_submission[submission_id] = event_type
    return latest_by_submission


def _submission_with_scores(db: Session, submission: Submission) -> SubmissionListItem:
    total_for_address = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(
            Submission.case_id == submission.case_id,
            Submission.chain == submission.chain,
            Submission.address == submission.address,
        )
    )
    matching_same_label = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(
            Submission.case_id == submission.case_id,
            Submission.chain == submission.chain,
            Submission.address == submission.address,
            Submission.scam_type == submission.scam_type,
        )
    )

    contractor_accepted = db.scalar(
        select(func.count())
        .select_from(SubmissionEvent)
        .join(Submission, Submission.submission_id == SubmissionEvent.submission_id)
        .where(
            Submission.contractor_id == submission.contractor_id,
            SubmissionEvent.event_type == "APPROVED",
        )
    )
    contractor_rejected = db.scalar(
        select(func.count())
        .select_from(SubmissionEvent)
        .join(Submission, Submission.submission_id == SubmissionEvent.submission_id)
        .where(
            Submission.contractor_id == submission.contractor_id,
            SubmissionEvent.event_type == "REJECTED",
        )
    )

    validation_payload = _latest_validated_payload(db, submission.submission_id)
    is_duplicate = bool(validation_payload.get("duplicate_of"))
    is_conflicted = bool(validation_payload.get("conflict_with"))

    consensus = compute_consensus_score(matching_same_label or 0, total_for_address or 0)
    reliability = compute_contractor_reliability(contractor_accepted or 0, contractor_rejected or 0)
    triage_priority = compute_triage_priority(
        contractor_reliability=reliability,
        consensus_score=consensus,
        confidence_score=submission.confidence_score,
    )

    return SubmissionListItem(
        submission_id=UUID(submission.submission_id),
        case_id=UUID(submission.case_id),
        contractor_id=UUID(submission.contractor_id),
        chain=submission.chain,
        address=submission.address,
        scam_type=submission.scam_type,
        source_url=submission.source_url,
        confidence_score=submission.confidence_score,
        created_at=submission.created_at,
        submission_hash=submission.submission_hash,
        latest_event_type=_get_latest_event_type(db, submission.submission_id),
        is_duplicate=is_duplicate,
        is_conflicted=is_conflicted,
        triage_priority=triage_priority,
    )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cases", response_model=CaseResponse)
def create_case(
    payload: CreateCaseRequest,
    db: Session = Depends(get_db_session),
) -> CaseResponse:
    start, deadline = derive_case_times(payload.start_time, payload.deadline_time)
    case = Case(
        title=payload.title,
        priority=payload.priority.value,
        start_time=start,
        deadline_time=deadline,
        status="OPEN",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return CaseResponse(
        case_id=UUID(case.case_id),
        title=case.title,
        priority=case.priority,
        start_time=case.start_time,
        deadline_time=case.deadline_time,
        status=case.status,
    )


@app.get("/cases", response_model=list[CaseResponse])
def list_cases(db: Session = Depends(get_db_session)) -> list[CaseResponse]:
    rows = db.scalars(select(Case).order_by(desc(Case.start_time))).all()
    return [
        CaseResponse(
            case_id=UUID(row.case_id),
            title=row.title,
            priority=row.priority,
            start_time=row.start_time,
            deadline_time=row.deadline_time,
            status=row.status,
        )
        for row in rows
    ]


@app.post("/cases/{case_id}/submit", response_model=SubmitResponse)
def submit_intelligence(
    case_id: UUID,
    payload: SubmitRequest,
    db: Session = Depends(get_db_session),
) -> SubmitResponse:
    case = db.get(Case, str(case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    contractor = db.get(Contractor, str(payload.contractor_id))
    if contractor is None:
        raise HTTPException(status_code=404, detail="contractor_not_found")

    incoming_payload = payload.model_dump(by_alias=True, mode="json")
    existing_same_case = db.scalars(
        select(Submission).where(Submission.case_id == str(case_id))
    ).all()

    validation = validate_submission(
        chain=payload.chain.value,
        address=payload.address,
        source_url=str(payload.source_url),
        scam_type=payload.scam_type.value,
        existing_same_case=existing_same_case,
    )

    canonical_payload = {
        "case_id": str(case_id),
        "payload": incoming_payload,
        "normalized_chain": validation.normalized_chain,
        "normalized_address": validation.normalized_address,
    }

    submission = Submission(
        case_id=str(case_id),
        contractor_id=str(payload.contractor_id),
        chain=validation.normalized_chain,
        address=validation.normalized_address,
        scam_type=payload.scam_type.value,
        source_url=str(payload.source_url),
        confidence_score=payload.confidence_score,
        raw_payload_json=canonical_json(incoming_payload),
        submission_hash=submission_hash(canonical_payload),
    )
    db.add(submission)
    db.flush()

    _create_event(
        db,
        submission_id=submission.submission_id,
        event_type=EventType.INGESTED.value,
        payload={"submission_hash": submission.submission_hash},
        actor=str(payload.contractor_id),
    )

    validation_payload = {
        "passed": validation.passed,
        "reasons": validation.reasons,
        "normalized_chain": validation.normalized_chain,
        "normalized_address": validation.normalized_address,
        "duplicate_of": validation.duplicate_of,
        "conflict_with": validation.conflict_with,
    }
    _create_event(
        db,
        submission_id=submission.submission_id,
        event_type=EventType.VALIDATED.value,
        payload=validation_payload,
        actor="system",
    )

    if validation.conflict_with:
        _create_event(
            db,
            submission_id=submission.submission_id,
            event_type=EventType.CONFLICTED.value,
            payload={"conflict_with": validation.conflict_with},
            actor="system",
        )

    db.commit()

    return SubmitResponse(
        submission_id=UUID(submission.submission_id),
        submission_hash=submission.submission_hash,
        validation=ValidationResult(**validation_payload),
    )


@app.get("/cases/{case_id}/submissions", response_model=list[SubmissionListItem])
def list_case_submissions(
    case_id: UUID,
    db: Session = Depends(get_db_session),
) -> list[SubmissionListItem]:
    case = db.get(Case, str(case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    submissions = db.scalars(
        select(Submission)
        .where(Submission.case_id == str(case_id))
        .order_by(desc(Submission.created_at))
    ).all()
    return [_submission_with_scores(db, row) for row in submissions]


@app.get("/submissions/{submission_id}", response_model=SubmissionDetail)
def get_submission_detail(
    submission_id: UUID,
    db: Session = Depends(get_db_session),
) -> SubmissionDetail:
    submission = db.get(Submission, str(submission_id))
    if submission is None:
        raise HTTPException(status_code=404, detail="submission_not_found")

    events = db.scalars(
        select(SubmissionEvent)
        .where(SubmissionEvent.submission_id == str(submission_id))
        .order_by(SubmissionEvent.created_at)
    ).all()

    return SubmissionDetail(
        item=_submission_with_scores(db, submission),
        events=[
            SubmissionEventResponse(
                event_id=UUID(event.event_id),
                event_type=event.event_type,
                event_payload_json=json.loads(event.event_payload_json),
                created_at=event.created_at,
                actor=event.actor,
            )
            for event in events
        ],
    )


@app.post("/submissions/{submission_id}/actions")
def submission_action(
    submission_id: UUID,
    payload: ManagerActionRequest,
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    submission = db.get(Submission, str(submission_id))
    if submission is None:
        raise HTTPException(status_code=404, detail="submission_not_found")

    event_type = ACTION_TO_EVENT[payload.action.value]
    event = _create_event(
        db,
        submission_id=str(submission_id),
        event_type=event_type,
        payload={"notes": payload.notes or "", "action": payload.action.value},
        actor=payload.actor,
    )
    db.commit()

    return JSONResponse(
        {
            "ok": True,
            "event_id": event.event_id,
            "submission_id": str(submission_id),
            "event_type": event_type,
        }
    )


@app.get("/cases/{case_id}/export")
def export_case(
    case_id: UUID,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db_session),
) -> Response:
    case = db.get(Case, str(case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    latest_event_types = _latest_event_type_map_for_case(db, str(case_id))
    approved_ids = [
        sid
        for sid, event_type in latest_event_types.items()
        if event_type == EventType.APPROVED.value
    ]
    if len(approved_ids) == 0:
        records: list[ExportRecord] = []
    else:
        approved_rows = db.scalars(
            select(Submission).where(
                Submission.case_id == str(case_id),
                Submission.submission_id.in_(approved_ids),
            )
        ).all()
        records = []
        for row in approved_rows:
            validation_summary = _latest_validated_payload(db, row.submission_id)
            records.append(
                ExportRecord(
                    case_id=UUID(row.case_id),
                    submission_id=UUID(row.submission_id),
                    contractor_id=UUID(row.contractor_id),
                    created_at=row.created_at,
                    chain=row.chain,
                    address=row.address,
                    scam_type=row.scam_type,
                    source_url=row.source_url,
                    confidence_score=row.confidence_score,
                    submission_hash=row.submission_hash,
                    validation_summary=validation_summary,
                )
            )
            _create_event(
                db,
                submission_id=row.submission_id,
                event_type=EventType.EXPORTED.value,
                payload={"format": format, "exported_at": datetime.utcnow().isoformat()},
                actor="system",
            )
        db.commit()

    if format == "json":
        return JSONResponse([record.model_dump(mode="json") for record in records])

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "submission_id",
            "contractor_id",
            "created_at",
            "chain",
            "address",
            "scam_type",
            "source_url",
            "confidence_score",
            "submission_hash",
            "validation_summary",
        ],
    )
    writer.writeheader()
    for record in records:
        row = record.model_dump(mode="json")
        row["validation_summary"] = canonical_json(row["validation_summary"])
        writer.writerow(row)

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    headers = {"Content-Disposition": f"attachment; filename=sentinel_export_{now}.csv"}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)
