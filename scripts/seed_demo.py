from __future__ import annotations

import argparse
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from sentinel.db import DB_PATH, SessionLocal
from sentinel.hashing import canonical_json, submission_hash
from sentinel.models import Case, Contractor, Submission, SubmissionEvent

# Maintained for compatibility with verifier monkeypatch contracts.
engine = None


def random_eth_address() -> str:
    return "0x" + "".join(random.choice("0123456789abcdef") for _ in range(40))


def _reset_dataset(db) -> None:
    db.execute(delete(SubmissionEvent))
    db.execute(delete(Submission))
    db.execute(delete(Contractor))
    db.execute(delete(Case))
    db.commit()


def _has_expected_seed_shape(db) -> bool:
    return (
        db.query(Case).count() == 1
        and db.query(Contractor).count() == 50
        and db.query(Submission).count() == 2000
    )


def main(*, reset: bool = False) -> None:
    random.seed(42)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        if db.query(Case).count() > 0:
            if reset:
                _reset_dataset(db)
            elif _has_expected_seed_shape(db):
                print("Seed skipped: expected demo dataset already present")
                return
            else:
                print("Seed aborted: existing non-demo data present (run with --reset)")
                return

        now = datetime.now(UTC)
        case = Case(
            title="Demo Investigation",
            priority="HIGH",
            start_time=now,
            deadline_time=now + timedelta(hours=72),
            status="OPEN",
        )
        db.add(case)
        db.flush()

        contractors = []
        for i in range(50):
            contractor = Contractor(contractor_id=str(uuid.uuid4()), handle=f"ct_{i:02d}")
            contractors.append(contractor)
            db.add(contractor)
        db.flush()

        scam_types = ["Phishing", "PigButchering", "Rugpull", "Exchange", "Other"]
        address_pool = [random_eth_address() for _ in range(1200)]

        def insert_submission(
            *,
            contractor_id: str,
            address: str,
            scam_type: str,
            duplicate_of: list[str],
            conflict_with: list[str],
        ) -> str:
            payload = {
                "contractor_id": contractor_id,
                "blockchain": "ETH",
                "address": address,
                "scam_type": scam_type,
                "source_url": "https://example.com/evidence",
                "confidence_score": random.randint(1, 5),
            }
            submission = Submission(
                case_id=case.case_id,
                contractor_id=contractor_id,
                chain="ETH",
                address=address,
                scam_type=scam_type,
                source_url=payload["source_url"],
                confidence_score=payload["confidence_score"],
                raw_payload_json=canonical_json(payload),
                submission_hash=submission_hash({"case_id": case.case_id, "payload": payload}),
            )
            db.add(submission)
            db.flush()

            db.add(
                SubmissionEvent(
                    submission_id=submission.submission_id,
                    event_type="INGESTED",
                    event_payload_json=canonical_json({"seed": True}),
                    actor=contractor_id,
                )
            )
            db.add(
                SubmissionEvent(
                    submission_id=submission.submission_id,
                    event_type="VALIDATED",
                    event_payload_json=canonical_json(
                        {
                            "passed": True,
                            "reasons": [],
                            "normalized_chain": "ETH",
                            "normalized_address": address,
                            "duplicate_of": duplicate_of,
                            "conflict_with": conflict_with,
                        }
                    ),
                    actor="system",
                )
            )
            if conflict_with:
                db.add(
                    SubmissionEvent(
                        submission_id=submission.submission_id,
                        event_type="CONFLICTED",
                        event_payload_json=canonical_json({"conflict_with": conflict_with}),
                        actor="system",
                    )
                )
            return submission.submission_id

        seen_by_key: dict[tuple[str, str], tuple[str, str]] = {}
        total = 2000
        conflict_window = 250

        for i in range(total):
            contractor = contractors[i % len(contractors)]

            if i < conflict_window:
                anchor_idx = i // 2
                address = address_pool[anchor_idx]
                if i % 2 == 0:
                    scam_type = scam_types[anchor_idx % len(scam_types)]
                else:
                    scam_type = scam_types[(anchor_idx + 1) % len(scam_types)]
            else:
                address = random.choice(address_pool)
                scam_type = random.choice(scam_types)

            key = ("ETH", address)
            duplicate_of: list[str] = []
            conflict_with: list[str] = []
            if key in seen_by_key:
                first_id, first_scam = seen_by_key[key]
                duplicate_of = [first_id]
                if first_scam != scam_type:
                    conflict_with = [first_id]

            submission_id = insert_submission(
                contractor_id=contractor.contractor_id,
                address=address,
                scam_type=scam_type,
                duplicate_of=duplicate_of,
                conflict_with=conflict_with,
            )
            if key not in seen_by_key:
                seen_by_key[key] = (submission_id, scam_type)

        db.commit()
        print("Seeded demo data")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed deterministic Sentinel-Ops demo dataset")
    parser.add_argument("--reset", action="store_true", help="clear existing data before seeding")
    args = parser.parse_args()
    main(reset=args.reset)
