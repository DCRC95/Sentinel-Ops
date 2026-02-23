from __future__ import annotations

# [verifier: ARBITER-RHYS-01]
import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, distinct, func, select
from sqlalchemy.orm import Session, sessionmaker

import scripts.seed_demo as seed_demo
from app.main import app
from sentinel.db import get_db_session
from sentinel.events import ALL_EVENT_TYPES
from sentinel.hashing import submission_hash
from sentinel.models import Base, Case, Contractor, Submission, SubmissionEvent
from sentinel.validation import validate_submission


@pytest.fixture()
def db_session_factory(tmp_path: Path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, class_=Session
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal, engine, db_file
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session_factory):
    TestingSessionLocal, _, _ = db_session_factory

    def override_get_db_session():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as c:
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()


def _create_case(client: TestClient) -> str:
    response = client.post("/cases", json={"title": "Case A", "priority": "HIGH"})
    assert response.status_code == 200
    return response.json()["case_id"]


def _create_contractor(session_factory: sessionmaker[Session], handle: str = "ct_01") -> str:
    contractor_id = str(uuid.uuid4())
    contractor = Contractor(contractor_id=contractor_id, handle=handle)
    with session_factory() as db:
        db.add(contractor)
        db.commit()
    return contractor_id


def _submit_payload(
    contractor_id: str, address: str, scam_type: str = "Phishing"
) -> dict[str, object]:
    return {
        "contractor_id": contractor_id,
        "blockchain": "ETH",
        "address": address,
        "scam_type": scam_type,
        "source_url": "https://example.com/evidence",
        "confidence_score": 5,
    }


# A) Append-only provenance


def test_a_append_only_provenance_and_latest_status(client):
    api, session_factory = client
    case_id = _create_case(api)
    contractor_id = _create_contractor(session_factory)

    submit = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(
            contractor_id=contractor_id, address="0x1111111111111111111111111111111111111111"
        ),
    )
    assert submit.status_code == 200
    submission_id = submit.json()["submission_id"]

    with session_factory() as db:
        submission_before = db.get(Submission, submission_id)
        assert submission_before is not None
        before_created_at = submission_before.created_at
        initial_events = db.scalars(
            select(SubmissionEvent).where(SubmissionEvent.submission_id == submission_id)
        ).all()
        initial_event_ids = [event.event_id for event in initial_events]
        assert len(initial_events) == 2

    approve = api.post(
        f"/submissions/{submission_id}/actions",
        json={"action": "approve", "actor": "manager_1", "notes": "ok"},
    )
    assert approve.status_code == 200

    reject = api.post(
        f"/submissions/{submission_id}/actions",
        json={"action": "reject", "actor": "manager_2", "notes": "new intel"},
    )
    assert reject.status_code == 200

    detail = api.get(f"/submissions/{submission_id}")
    assert detail.status_code == 200
    detail_json = detail.json()

    with session_factory() as db:
        submission_after = db.get(Submission, submission_id)
        assert submission_after is not None
        assert submission_after.created_at == before_created_at

        all_events = db.scalars(
            select(SubmissionEvent)
            .where(SubmissionEvent.submission_id == submission_id)
            .order_by(SubmissionEvent.created_at)
        ).all()

    assert len(all_events) == 4
    assert all(
        event_id in [event.event_id for event in all_events] for event_id in initial_event_ids
    )
    assert detail_json["item"]["latest_event_type"] == "REJECTED"


# B) Deterministic validation and hashing


def test_b_validation_and_hashing_are_deterministic_for_same_payload():
    existing: list[Submission] = []
    kwargs = {
        "chain": "ETH",
        "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "source_url": "https://example.com/source",
        "scam_type": "Phishing",
        "existing_same_case": existing,
    }

    validation_1 = validate_submission(**kwargs)
    validation_2 = validate_submission(**kwargs)

    assert validation_1 == validation_2

    payload_a = {
        "case_id": "case-123",
        "payload": {
            "contractor_id": "ct-1",
            "blockchain": "ETH",
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "scam_type": "Phishing",
            "source_url": "https://example.com/source",
            "confidence_score": 3,
        },
        "normalized_chain": "ETH",
        "normalized_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
    payload_b = {
        "normalized_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "payload": {
            "confidence_score": 3,
            "source_url": "https://example.com/source",
            "scam_type": "Phishing",
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "blockchain": "ETH",
            "contractor_id": "ct-1",
        },
        "case_id": "case-123",
        "normalized_chain": "ETH",
    }

    assert submission_hash(payload_a) == submission_hash(payload_b)


# C) Conflict and dedupe correctness


def test_c_conflict_and_dedupe_events_reference_prior_submission(client):
    api, session_factory = client
    case_id = _create_case(api)
    contractor_a = _create_contractor(session_factory, handle="ct_a")
    contractor_b = _create_contractor(session_factory, handle="ct_b")
    contractor_c = _create_contractor(session_factory, handle="ct_c")
    conflict_address = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    dedupe_address = "0xabababababababababababababababababababab"

    first = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(contractor_a, address=conflict_address, scam_type="Phishing"),
    )
    assert first.status_code == 200
    first_id = first.json()["submission_id"]

    second = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(contractor_b, address=conflict_address, scam_type="Rugpull"),
    )
    assert second.status_code == 200

    dedupe_base = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(contractor_c, address=dedupe_address, scam_type="Exchange"),
    )
    assert dedupe_base.status_code == 200
    dedupe_base_id = dedupe_base.json()["submission_id"]

    dedupe_followup = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(contractor_a, address=dedupe_address, scam_type="Exchange"),
    )
    assert dedupe_followup.status_code == 200

    second_payload = second.json()["validation"]
    assert first_id in second_payload["conflict_with"]
    assert first_id in second_payload["duplicate_of"]

    second_detail = api.get(f"/submissions/{second.json()['submission_id']}")
    assert second_detail.status_code == 200
    second_events = {event["event_type"] for event in second_detail.json()["events"]}
    assert "CONFLICTED" in second_events

    dedupe_payload = dedupe_followup.json()["validation"]
    assert dedupe_base_id in dedupe_payload["duplicate_of"]
    assert dedupe_payload["conflict_with"] == []


# D) Export correctness


def test_d_export_only_contains_approved_with_required_provenance_fields(client):
    api, session_factory = client
    case_id = _create_case(api)
    contractor_id = _create_contractor(session_factory)

    approved = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(
            contractor_id,
            address="0xcccccccccccccccccccccccccccccccccccccccc",
            scam_type="Phishing",
        ),
    )
    rejected = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(
            contractor_id, address="0xdddddddddddddddddddddddddddddddddddddddd", scam_type="Rugpull"
        ),
    )
    pending = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(
            contractor_id,
            address="0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            scam_type="Exchange",
        ),
    )

    assert approved.status_code == rejected.status_code == pending.status_code == 200

    approve_action = api.post(
        f"/submissions/{approved.json()['submission_id']}/actions",
        json={"action": "approve", "actor": "manager", "notes": "ok"},
    )
    reject_action = api.post(
        f"/submissions/{rejected.json()['submission_id']}/actions",
        json={"action": "reject", "actor": "manager", "notes": "bad"},
    )
    assert approve_action.status_code == reject_action.status_code == 200

    export_json = api.get(f"/cases/{case_id}/export?format=json")
    assert export_json.status_code == 200
    records = export_json.json()
    assert len(records) == 1

    record = records[0]
    required_fields = {
        "case_id",
        "submission_id",
        "contractor_id",
        "created_at",
        "source_url",
        "validation_summary",
    }
    assert required_fields.issubset(record.keys())
    assert record["submission_id"] == approved.json()["submission_id"]


# E) Seed/demo realism


def test_e_seed_creates_expected_realistic_dataset(db_session_factory, monkeypatch):
    TestingSessionLocal, engine, db_file = db_session_factory

    monkeypatch.setattr(seed_demo, "DB_PATH", db_file)
    monkeypatch.setattr(seed_demo, "engine", engine)
    monkeypatch.setattr(seed_demo, "SessionLocal", TestingSessionLocal)

    seed_demo.main()

    with TestingSessionLocal() as db:
        case_count = db.query(Case).count()
        contractor_count = db.query(Contractor).count()
        submission_count = db.query(Submission).count()

        duplicate_pairs = db.execute(
            select(Submission.chain, Submission.address)
            .group_by(Submission.chain, Submission.address)
            .having(func.count() > 1)
        ).all()

        conflict_pairs = db.execute(
            select(Submission.chain, Submission.address)
            .group_by(Submission.chain, Submission.address)
            .having(func.count(distinct(Submission.scam_type)) > 1)
        ).all()

    assert case_count == 1
    assert contractor_count == 50
    assert submission_count == 2000
    assert len(duplicate_pairs) > 0
    assert len(conflict_pairs) > 0


# F) Docs and implementation consistency + API smoke tests


def _normalize_path_template(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def _documented_endpoints(api_spec_text: str) -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    for line in api_spec_text.splitlines():
        match = re.match(r"^##\s+(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)", line.strip())
        if match:
            method, path = match.groups()
            endpoints.add((method, _normalize_path_template(path)))
    return endpoints


def _implemented_endpoints() -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    for route in app.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", None)
        if not path:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            endpoints.add((method, _normalize_path_template(path)))
    return endpoints


def _documented_event_types(event_model_text: str) -> set[str]:
    values: set[str] = set()
    for line in event_model_text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            candidate = line[2:].strip()
            if candidate and candidate.upper() == candidate and " " not in candidate:
                values.add(candidate)
    return values


def _implemented_event_types() -> set[str]:
    return set(ALL_EVENT_TYPES)


def test_f_docs_code_consistency():
    api_spec = Path("docs/API_SPEC.md").read_text(encoding="utf-8")
    event_model = Path("docs/EVENT_MODEL.md").read_text(encoding="utf-8")

    documented_endpoints = _documented_endpoints(api_spec)
    implemented_endpoints = _implemented_endpoints()

    missing = documented_endpoints - implemented_endpoints
    assert not missing, f"Documented endpoints missing in code: {sorted(missing)}"

    documented_event_types = _documented_event_types(event_model)
    implemented_event_types = _implemented_event_types()
    assert documented_event_types == implemented_event_types


def test_f_api_smoke(client):
    api, session_factory = client

    health = api.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    case_id = _create_case(api)
    cases = api.get("/cases")
    assert cases.status_code == 200
    assert any(c["case_id"] == case_id for c in cases.json())

    contractor_id = _create_contractor(session_factory)
    submission = api.post(
        f"/cases/{case_id}/submit",
        json=_submit_payload(
            contractor_id, "0xffffffffffffffffffffffffffffffffffffffff", "Phishing"
        ),
    )
    assert submission.status_code == 200
    submission_id = submission.json()["submission_id"]

    listed = api.get(f"/cases/{case_id}/submissions")
    assert listed.status_code == 200
    assert any(item["submission_id"] == submission_id for item in listed.json())

    detail = api.get(f"/submissions/{submission_id}")
    assert detail.status_code == 200

    action = api.post(
        f"/submissions/{submission_id}/actions",
        json={"action": "approve", "actor": "manager", "notes": "ok"},
    )
    assert action.status_code == 200

    export = api.get(f"/cases/{case_id}/export?format=json")
    assert export.status_code == 200
    body = export.json()
    assert isinstance(body, list)
