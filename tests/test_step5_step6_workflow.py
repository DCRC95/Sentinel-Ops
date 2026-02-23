from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from sentinel.db import engine, get_db_session
from sentinel.models import Base, Contractor, SubmissionEvent


class DbContext:
    def __init__(self) -> None:
        self.session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            class_=Session,
        )

    def override(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()


def _create_contractor(session_factory: sessionmaker[Session], handle: str) -> str:
    contractor_id = str(uuid.uuid4())
    with session_factory() as db:
        db.add(Contractor(contractor_id=contractor_id, handle=handle))
        db.commit()
    return contractor_id


def _submit(
    client: TestClient,
    *,
    case_id: str,
    contractor_id: str,
    address: str,
    scam_type: str,
    confidence_score: int,
):
    return client.post(
        f"/cases/{case_id}/submit",
        json={
            "contractor_id": contractor_id,
            "blockchain": "ETH",
            "address": address,
            "scam_type": scam_type,
            "source_url": "https://example.com/evidence",
            "confidence_score": confidence_score,
        },
    )


def test_step5_list_submissions_derives_status_and_flags() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ctx = DbContext()
    app.dependency_overrides[get_db_session] = ctx.override

    with TestClient(app) as client:
        case_resp = client.post("/cases", json={"title": "Step5 Case", "priority": "HIGH"})
        assert case_resp.status_code == 200
        case_id = case_resp.json()["case_id"]

        c1 = _create_contractor(ctx.session_factory, "ct_s5_1")
        c2 = _create_contractor(ctx.session_factory, "ct_s5_2")

        address = "0xabababababababababababababababababababab"

        first = _submit(
            client,
            case_id=case_id,
            contractor_id=c1,
            address=address,
            scam_type="Phishing",
            confidence_score=5,
        )
        assert first.status_code == 200

        second = _submit(
            client,
            case_id=case_id,
            contractor_id=c2,
            address=address,
            scam_type="Rugpull",
            confidence_score=4,
        )
        assert second.status_code == 200

        listed = client.get(f"/cases/{case_id}/submissions")
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) == 2

        by_id = {row["submission_id"]: row for row in rows}
        first_row = by_id[first.json()["submission_id"]]
        second_row = by_id[second.json()["submission_id"]]

        assert first_row["latest_event_type"] == "VALIDATED"
        assert second_row["latest_event_type"] == "CONFLICTED"
        assert first_row["is_duplicate"] is False
        assert second_row["is_duplicate"] is True
        assert first_row["is_conflicted"] is False
        assert second_row["is_conflicted"] is True
        assert isinstance(first_row["triage_priority"], float)
        assert isinstance(second_row["triage_priority"], float)

    app.dependency_overrides.clear()


def test_step6_actions_append_event_and_update_latest_status() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ctx = DbContext()
    app.dependency_overrides[get_db_session] = ctx.override

    with TestClient(app) as client:
        case_resp = client.post("/cases", json={"title": "Step6 Case", "priority": "MED"})
        assert case_resp.status_code == 200
        case_id = case_resp.json()["case_id"]

        contractor_id = _create_contractor(ctx.session_factory, "ct_s6")
        submission = _submit(
            client,
            case_id=case_id,
            contractor_id=contractor_id,
            address="0x1111111111111111111111111111111111111111",
            scam_type="Phishing",
            confidence_score=3,
        )
        assert submission.status_code == 200
        submission_id = submission.json()["submission_id"]

        approve = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "approve", "actor": "manager_a", "notes": "looks good"},
        )
        assert approve.status_code == 200
        assert approve.json()["event_type"] == "APPROVED"

        escalate = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "escalate", "actor": "manager_b", "notes": "needs legal review"},
        )
        assert escalate.status_code == 200
        assert escalate.json()["event_type"] == "ESCALATED"

        detail = client.get(f"/submissions/{submission_id}")
        assert detail.status_code == 200
        assert detail.json()["item"]["latest_event_type"] == "ESCALATED"

        with ctx.session_factory() as db:
            events = db.scalars(
                select(SubmissionEvent)
                .where(SubmissionEvent.submission_id == submission_id)
                .order_by(SubmissionEvent.created_at)
            ).all()

        event_types = [event.event_type for event in events]
        assert event_types[:2] == ["INGESTED", "VALIDATED"]
        assert event_types[-2:] == ["APPROVED", "ESCALATED"]

    app.dependency_overrides.clear()
