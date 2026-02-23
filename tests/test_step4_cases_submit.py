from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from sentinel.db import get_db_session
from sentinel.models import Base, Contractor, SubmissionEvent


def _with_test_client(db_file: Path) -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db_session():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), TestingSessionLocal


def test_post_cases_and_submit_writes_ingested_validated_events(tmp_path: Path) -> None:
    client, session_factory = _with_test_client(tmp_path / "step4.db")

    with client:
        case_resp = client.post("/cases", json={"title": "Step4 Case", "priority": "HIGH"})
        assert case_resp.status_code == 200
        case_id = case_resp.json()["case_id"]

        contractor_id = str(uuid.uuid4())
        with session_factory() as db:
            db.add(Contractor(contractor_id=contractor_id, handle="ct_step4"))
            db.commit()

        submit_resp = client.post(
            f"/cases/{case_id}/submit",
            json={
                "contractor_id": contractor_id,
                "blockchain": "ETH",
                "address": "0x1111111111111111111111111111111111111111",
                "scam_type": "Phishing",
                "source_url": "https://example.com/evidence",
                "confidence_score": 5,
            },
        )

        assert submit_resp.status_code == 200
        submission_id = submit_resp.json()["submission_id"]

        with session_factory() as db:
            events = db.scalars(
                select(SubmissionEvent)
                .where(SubmissionEvent.submission_id == submission_id)
                .order_by(SubmissionEvent.created_at)
            ).all()

        assert [event.event_type for event in events][:2] == ["INGESTED", "VALIDATED"]

    app.dependency_overrides.clear()
