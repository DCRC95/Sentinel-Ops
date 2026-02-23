from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from sentinel.db import get_db_session
from sentinel.hashing import canonical_json
from sentinel.models import Base, Contractor, Submission, SubmissionEvent


def _setup_test_client(tmp_path):
    db_file = tmp_path / "invariants.db"
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
    client = TestClient(app)
    return client, session_factory


def _create_case(client: TestClient) -> str:
    resp = client.post("/cases", json={"title": "Invariant Case", "priority": "HIGH"})
    assert resp.status_code == 200
    return resp.json()["case_id"]


def _create_contractor(session_factory, handle: str = "ct_inv") -> str:
    contractor_id = str(uuid.uuid4())
    with session_factory() as db:
        db.add(Contractor(contractor_id=contractor_id, handle=handle))
        db.commit()
    return contractor_id


def _submit(client: TestClient, case_id: str, contractor_id: str, address: str, scam_type: str):
    return client.post(
        f"/cases/{case_id}/submit",
        json={
            "contractor_id": contractor_id,
            "blockchain": "ETH",
            "address": address,
            "scam_type": scam_type,
            "source_url": "https://example.com/evidence",
            "confidence_score": 5,
        },
    )


def test_invariant_1_validation_required_for_approval(tmp_path) -> None:
    client, session_factory = _setup_test_client(tmp_path)

    with client:
        case_id = _create_case(client)
        contractor_id = _create_contractor(session_factory)

        with session_factory() as db:
            submission = Submission(
                case_id=case_id,
                contractor_id=contractor_id,
                chain="ETH",
                address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                scam_type="Phishing",
                source_url="https://example.com/evidence",
                confidence_score=5,
                raw_payload_json=canonical_json({"synthetic": True}),
                submission_hash="synthetic-hash",
            )
            db.add(submission)
            db.flush()
            db.add(
                SubmissionEvent(
                    submission_id=submission.submission_id,
                    event_type="INGESTED",
                    event_payload_json=canonical_json({"synthetic": True}),
                    actor=contractor_id,
                )
            )
            db.commit()
            submission_id = submission.submission_id

        approve = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "approve", "actor": "manager", "notes": "should fail"},
        )
        assert approve.status_code == 409

    app.dependency_overrides.clear()


def test_invariant_2_export_requires_approval(tmp_path) -> None:
    client, session_factory = _setup_test_client(tmp_path)

    with client:
        case_id = _create_case(client)
        contractor_id = _create_contractor(session_factory)

        submit = _submit(
            client,
            case_id,
            contractor_id,
            "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "Phishing",
        )
        assert submit.status_code == 200

        export = client.get(f"/cases/{case_id}/export?format=json")
        assert export.status_code == 200
        assert export.json() == []

    app.dependency_overrides.clear()


def test_invariant_3_single_latest_state(tmp_path) -> None:
    client, session_factory = _setup_test_client(tmp_path)

    with client:
        case_id = _create_case(client)
        contractor_id = _create_contractor(session_factory)

        submit = _submit(
            client,
            case_id,
            contractor_id,
            "0xcccccccccccccccccccccccccccccccccccccccc",
            "Phishing",
        )
        assert submit.status_code == 200
        submission_id = submit.json()["submission_id"]

        approve = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "approve", "actor": "manager", "notes": "ok"},
        )
        assert approve.status_code == 200

        reject = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "reject", "actor": "manager", "notes": "new intel"},
        )
        assert reject.status_code == 200

        detail = client.get(f"/submissions/{submission_id}")
        assert detail.status_code == 200
        assert detail.json()["item"]["latest_event_type"] == "REJECTED"

    app.dependency_overrides.clear()


def test_invariant_4_event_immutability(tmp_path) -> None:
    client, session_factory = _setup_test_client(tmp_path)

    with client:
        case_id = _create_case(client)
        contractor_id = _create_contractor(session_factory)

        submit = _submit(
            client,
            case_id,
            contractor_id,
            "0xdddddddddddddddddddddddddddddddddddddddd",
            "Phishing",
        )
        assert submit.status_code == 200
        submission_id = submit.json()["submission_id"]

        with session_factory() as db:
            first_event = db.scalar(
                select(SubmissionEvent)
                .where(SubmissionEvent.submission_id == submission_id)
                .order_by(SubmissionEvent.created_at)
                .limit(1)
            )
            assert first_event is not None
            snapshot = {
                "event_id": first_event.event_id,
                "event_type": first_event.event_type,
                "payload": first_event.event_payload_json,
                "actor": first_event.actor,
                "created_at": first_event.created_at,
            }

        approve = client.post(
            f"/submissions/{submission_id}/actions",
            json={"action": "approve", "actor": "manager", "notes": "ok"},
        )
        assert approve.status_code == 200

        with session_factory() as db:
            first_event_after = db.get(SubmissionEvent, snapshot["event_id"])
            assert first_event_after is not None
            assert first_event_after.event_type == snapshot["event_type"]
            assert first_event_after.event_payload_json == snapshot["payload"]
            assert first_event_after.actor == snapshot["actor"]
            assert first_event_after.created_at == snapshot["created_at"]

    app.dependency_overrides.clear()


def test_invariant_5_conflict_references_valid_submission_ids(tmp_path) -> None:
    client, session_factory = _setup_test_client(tmp_path)

    with client:
        case_id = _create_case(client)
        c1 = _create_contractor(session_factory, handle="ct_a")
        c2 = _create_contractor(session_factory, handle="ct_b")

        address = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        first = _submit(client, case_id, c1, address, "Phishing")
        second = _submit(client, case_id, c2, address, "Rugpull")
        assert first.status_code == 200
        assert second.status_code == 200

        second_id = second.json()["submission_id"]
        with session_factory() as db:
            conflict_event = db.scalar(
                select(SubmissionEvent)
                .where(
                    SubmissionEvent.submission_id == second_id,
                    SubmissionEvent.event_type == "CONFLICTED",
                )
                .limit(1)
            )
            assert conflict_event is not None
            payload = json.loads(conflict_event.event_payload_json)
            refs = payload.get("conflict_with", [])
            assert len(refs) > 0
            for ref_id in refs:
                ref_submission = db.get(Submission, ref_id)
                assert ref_submission is not None

    app.dependency_overrides.clear()
