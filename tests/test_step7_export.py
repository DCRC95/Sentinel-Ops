from __future__ import annotations

import csv
import io
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from sentinel.db import engine, get_db_session
from sentinel.models import Base, Contractor, SubmissionEvent


def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _override(session_factory: sessionmaker[Session]):
    def _inner():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return _inner


def _seed_case_with_submission(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> tuple[str, str, str]:
    case_resp = client.post("/cases", json={"title": "Step7 Case", "priority": "HIGH"})
    assert case_resp.status_code == 200
    case_id = case_resp.json()["case_id"]

    contractor_id = str(uuid.uuid4())
    with session_factory() as db:
        db.add(Contractor(contractor_id=contractor_id, handle="ct_s7"))
        db.commit()

    submit_resp = client.post(
        f"/cases/{case_id}/submit",
        json={
            "contractor_id": contractor_id,
            "blockchain": "ETH",
            "address": "0x2222222222222222222222222222222222222222",
            "scam_type": "Phishing",
            "source_url": "https://example.com/evidence",
            "confidence_score": 4,
        },
    )
    assert submit_resp.status_code == 200
    submission_id = submit_resp.json()["submission_id"]
    return case_id, submission_id, contractor_id


def test_step7_export_json_csv_and_exported_event() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = _session_factory()
    app.dependency_overrides[get_db_session] = _override(session_factory)

    with TestClient(app) as client:
        case_id, submission_id, _ = _seed_case_with_submission(client, session_factory)

        client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "approve", "actor": "manager", "notes": "ok"},
        )

        export_json = client.get(f"/cases/{case_id}/export?format=json")
        assert export_json.status_code == 200
        body = export_json.json()
        assert len(body) == 1
        assert body[0]["submission_id"] == submission_id
        assert "validation_summary" in body[0]

        export_csv = client.get(f"/cases/{case_id}/export?format=csv")
        assert export_csv.status_code == 200
        assert export_csv.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(export_csv.text)))
        assert len(rows) == 1
        assert rows[0]["submission_id"] == submission_id
        assert rows[0]["validation_summary"]

        with session_factory() as db:
            exported_events = db.scalars(
                select(SubmissionEvent).where(
                    SubmissionEvent.submission_id == submission_id,
                    SubmissionEvent.event_type == "EXPORTED",
                )
            ).all()
        assert len(exported_events) >= 1

    app.dependency_overrides.clear()
