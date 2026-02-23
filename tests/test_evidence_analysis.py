from __future__ import annotations

import uuid
from pathlib import Path

import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.main as api_main
from app.main import app
from sentinel.db import get_db_session
from sentinel.intelligence.evidence_analyzer import run_evidence_analysis
from sentinel.models import Base, Contractor, SubmissionEvent


def test_evidence_analysis_deterministic_same_input() -> None:
    address = "0x1111111111111111111111111111111111111111"
    text = (
        "Report confirms phishing. "
        f"Address {address} linked to fake website impersonation campaign."
    )

    def fake_fetcher(_url: str):
        return text, True, ["Source reachable"]

    result_a = run_evidence_analysis(
        address=address,
        scam_type="Phishing",
        source_url="https://example.com/report",
        fetcher=fake_fetcher,
    )
    result_b = run_evidence_analysis(
        address=address,
        scam_type="Phishing",
        source_url="https://example.com/report",
        fetcher=fake_fetcher,
    )

    assert result_a == result_b


def test_missing_unreachable_url_handled_safely() -> None:
    def failing_fetcher(_url: str):
        raise requests.RequestException("unreachable")

    try:
        run_evidence_analysis(
            address="0x2222222222222222222222222222222222222222",
            scam_type="Rugpull",
            source_url="https://invalid.local",
            fetcher=failing_fetcher,
        )
    except Exception as exc:
        raise AssertionError(f"Analyzer should fail safely, got exception: {exc}") from exc


def _setup_client(tmp_path: Path):
    db_file = tmp_path / "evidence.db"
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


def test_analyzer_never_crashes_ingestion(monkeypatch, tmp_path: Path) -> None:
    client, session_factory = _setup_client(tmp_path)

    def broken_analyzer(**_kwargs):
        raise RuntimeError("forced analyzer failure")

    monkeypatch.setattr(api_main, "run_evidence_analysis", broken_analyzer)

    with client:
        case_resp = client.post("/cases", json={"title": "Evidence Case", "priority": "HIGH"})
        assert case_resp.status_code == 200
        case_id = case_resp.json()["case_id"]

        contractor_id = str(uuid.uuid4())
        with session_factory() as db:
            db.add(Contractor(contractor_id=contractor_id, handle="ct_evidence"))
            db.commit()

        submit = client.post(
            f"/cases/{case_id}/submit",
            json={
                "contractor_id": contractor_id,
                "blockchain": "ETH",
                "address": "0x3333333333333333333333333333333333333333",
                "scam_type": "Phishing",
                "source_url": "https://example.com/evidence",
                "confidence_score": 4,
            },
        )
        assert submit.status_code == 200
        submission_id = submit.json()["submission_id"]

        with session_factory() as db:
            evidence_event = db.scalar(
                select(SubmissionEvent)
                .where(
                    SubmissionEvent.submission_id == submission_id,
                    SubmissionEvent.event_type == "EVIDENCE_ANALYZED",
                )
                .limit(1)
            )
            assert evidence_event is not None
            assert "Analyzer failed safely" in evidence_event.event_payload_json

    app.dependency_overrides.clear()
