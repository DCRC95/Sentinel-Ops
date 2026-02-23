from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from sentinel.db import get_db_session
from sentinel.models import Base, Contractor
from sentinel.replay import ReplayEvent, reconstruct_submission_state


def _setup_client(tmp_path: Path):
    db_file = tmp_path / "replay.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db_session():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), session_factory


def test_replay_reconstructs_submission_state_from_event_history(tmp_path: Path) -> None:
    client, session_factory = _setup_client(tmp_path)

    with client:
        case_resp = client.post("/cases", json={"title": "Replay Case", "priority": "HIGH"})
        assert case_resp.status_code == 200
        case_id = case_resp.json()["case_id"]

        contractor_id = str(uuid.uuid4())
        with session_factory() as db:
            db.add(Contractor(contractor_id=contractor_id, handle="ct_replay"))
            db.commit()

        submit = client.post(
            f"/cases/{case_id}/submit",
            json={
                "contractor_id": contractor_id,
                "blockchain": "ETH",
                "address": "0x9999999999999999999999999999999999999999",
                "scam_type": "Phishing",
                "source_url": "https://example.com/evidence",
                "confidence_score": 5,
            },
        )
        assert submit.status_code == 200
        submission_id = submit.json()["submission_id"]

        approve = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "approve", "actor": "manager", "notes": "approved"},
        )
        assert approve.status_code == 200

        export = client.get(f"/cases/{case_id}/export?format=json")
        assert export.status_code == 200

        detail = client.get(f"/submissions/{submission_id}")
        assert detail.status_code == 200
        detail_json = detail.json()

        replay_events = [
            ReplayEvent(
                event_type=event["event_type"],
                created_at=event["created_at"],
                event_payload=event["event_payload_json"],
            )
            for event in detail_json["events"]
        ]
        reconstructed = reconstruct_submission_state(replay_events)

        api_state = {
            "latest_event_type": detail_json["item"]["latest_event_type"],
            "is_conflicted": detail_json["item"]["is_conflicted"],
            "validation": next(
                (
                    e["event_payload_json"]
                    for e in detail_json["events"]
                    if e["event_type"] == "VALIDATED"
                ),
                {},
            ),
        }
        replay_state = {
            "latest_event_type": reconstructed.latest_event_type,
            "is_conflicted": reconstructed.conflicted,
            "validation": {
                "duplicate_of": reconstructed.duplicate_of,
                "conflict_with": reconstructed.conflict_with,
            },
        }

        assert replay_state["latest_event_type"] == api_state["latest_event_type"]
        assert replay_state["is_conflicted"] == api_state["is_conflicted"]
        assert replay_state["validation"]["duplicate_of"] == api_state["validation"].get(
            "duplicate_of", []
        )
        assert replay_state["validation"]["conflict_with"] == api_state["validation"].get(
            "conflict_with", []
        )
        assert reconstructed.validated is True
        assert reconstructed.approved is True
        assert reconstructed.exported is True

    app.dependency_overrides.clear()
