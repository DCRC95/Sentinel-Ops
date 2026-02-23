from __future__ import annotations

from pydantic import ValidationError

from sentinel.hashing import submission_hash
from sentinel.schemas import SubmitRequest


def test_submit_schema_accepts_blockchain_alias() -> None:
    payload = {
        "contractor_id": "c562c7e8-c093-4a13-8f65-fb8d39d97f88",
        "blockchain": "ETH",
        "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "scam_type": "Phishing",
        "source_url": "https://example.com/evidence",
        "confidence_score": 4,
    }

    parsed = SubmitRequest.model_validate(payload)
    assert parsed.chain.value == "ETH"


def test_submit_schema_accepts_chain_field_name() -> None:
    payload = {
        "contractor_id": "da4f9d15-d036-4a15-a5e3-ec47ee89cb4a",
        "chain": "BTC",
        "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7k3l8u3q",
        "scam_type": "Exchange",
        "source_url": "https://example.com/evidence",
        "confidence_score": 3,
    }

    parsed = SubmitRequest.model_validate(payload)
    assert parsed.chain.value == "BTC"


def test_submit_schema_rejects_unknown_fields() -> None:
    payload = {
        "contractor_id": "94283569-4fbe-4fcf-a0f8-6e094f6ee6b4",
        "blockchain": "ETH",
        "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "scam_type": "Rugpull",
        "source_url": "https://example.com/evidence",
        "confidence_score": 2,
        "unknown_field": "not-allowed",
    }

    try:
        SubmitRequest.model_validate(payload)
    except ValidationError:
        return

    raise AssertionError("SubmitRequest should reject unexpected fields")


def test_submission_hash_is_deterministic_for_key_order() -> None:
    payload_a = {
        "case_id": "case-1",
        "payload": {
            "contractor_id": "ct-1",
            "blockchain": "ETH",
            "address": "0xcccccccccccccccccccccccccccccccccccccccc",
            "scam_type": "Phishing",
            "source_url": "https://example.com/source",
            "confidence_score": 5,
        },
        "normalized_chain": "ETH",
        "normalized_address": "0xcccccccccccccccccccccccccccccccccccccccc",
    }

    payload_b = {
        "normalized_address": "0xcccccccccccccccccccccccccccccccccccccccc",
        "normalized_chain": "ETH",
        "payload": {
            "confidence_score": 5,
            "source_url": "https://example.com/source",
            "scam_type": "Phishing",
            "address": "0xcccccccccccccccccccccccccccccccccccccccc",
            "blockchain": "ETH",
            "contractor_id": "ct-1",
        },
        "case_id": "case-1",
    }

    assert submission_hash(payload_a) == submission_hash(payload_b)
