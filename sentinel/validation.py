from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

from sentinel.models import Submission

ETH_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
BTC_RE = re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$")
SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


@dataclass(frozen=True)
class ValidationPayload:
    passed: bool
    reasons: list[str]
    normalized_chain: str
    normalized_address: str
    duplicate_of: list[str]
    conflict_with: list[str]


def normalize_chain(chain: str) -> str:
    return chain.upper().strip()


def normalize_address(address: str) -> str:
    return address.strip()


def _valid_address(chain: str, address: str) -> bool:
    matcher = {
        "ETH": ETH_RE,
        "BTC": BTC_RE,
        "SOL": SOL_RE,
    }.get(chain)
    if matcher is None:
        return False
    return bool(matcher.match(address))


def _valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_submission(
    *,
    chain: str,
    address: str,
    source_url: str,
    scam_type: str,
    existing_same_case: Iterable[Submission],
) -> ValidationPayload:
    normalized_chain = normalize_chain(chain)
    normalized_address = normalize_address(address)

    reasons: list[str] = []
    duplicates: list[str] = []
    conflicts: list[str] = []

    if normalized_chain not in {"ETH", "BTC", "SOL"}:
        reasons.append("unsupported_chain")

    if not _valid_address(normalized_chain, normalized_address):
        reasons.append("invalid_address_format")

    if not _valid_url(source_url):
        reasons.append("invalid_source_url")

    for existing in existing_same_case:
        if existing.chain == normalized_chain and existing.address == normalized_address:
            duplicates.append(existing.submission_id)
            if existing.scam_type != scam_type:
                conflicts.append(existing.submission_id)

    passed = len(reasons) == 0
    return ValidationPayload(
        passed=passed,
        reasons=sorted(set(reasons)),
        normalized_chain=normalized_chain,
        normalized_address=normalized_address,
        duplicate_of=sorted(set(duplicates)),
        conflict_with=sorted(set(conflicts)),
    )
