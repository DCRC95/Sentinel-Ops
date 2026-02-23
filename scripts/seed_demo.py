from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sentinel.db import DB_PATH, SessionLocal, engine
from sentinel.hashing import canonical_json, submission_hash
from sentinel.models import Base, Case, Contractor, Submission, SubmissionEvent


def random_eth_address() -> str:
    return "0x" + "".join(random.choice("0123456789abcdef") for _ in range(40))


def main() -> None:
    random.seed(42)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Case).count() > 0:
            print("Seed skipped: existing data present")
            return

        now = datetime.now(timezone.utc)
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
        for i in range(10):
            contractor = Contractor(contractor_id=str(uuid.uuid4()), handle=f"ct_{i:02d}")
            contractors.append(contractor)
            db.add(contractor)
        db.flush()

        scam_types = ["Phishing", "PigButchering", "Rugpull", "Exchange", "Other"]

        for _ in range(100):
            contractor = random.choice(contractors)
            payload = {
                "contractor_id": contractor.contractor_id,
                "blockchain": "ETH",
                "address": random_eth_address(),
                "scam_type": random.choice(scam_types),
                "source_url": "https://example.com/evidence",
                "confidence_score": random.randint(1, 5),
            }
            submission = Submission(
                case_id=case.case_id,
                contractor_id=contractor.contractor_id,
                chain="ETH",
                address=payload["address"],
                scam_type=payload["scam_type"],
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
                    actor=contractor.contractor_id,
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
                            "normalized_address": payload["address"],
                            "duplicate_of": [],
                            "conflict_with": [],
                        }
                    ),
                    actor="system",
                )
            )

        db.commit()
        print("Seeded demo data")
    finally:
        db.close()


if __name__ == "__main__":
    main()
