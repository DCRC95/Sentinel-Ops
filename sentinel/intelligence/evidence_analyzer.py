from __future__ import annotations

import re
from collections.abc import Callable
from html import unescape

import requests

from sentinel.intelligence.models import EvidenceAnalysisResult
from sentinel.intelligence.rules import address_found, build_keyword_notes, keyword_match_score

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(raw: str) -> str:
    text = TAG_RE.sub(" ", raw)
    text = unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def fetch_evidence_text(source_url: str, timeout: int = 8) -> tuple[str, bool, list[str]]:
    try:
        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        return "", False, [f"Source unreachable: {type(exc).__name__}"]

    return _strip_html(response.text), True, ["Source reachable"]


def run_evidence_analysis(
    *,
    address: str,
    scam_type: str,
    source_url: str,
    fetcher: Callable[[str], tuple[str, bool, list[str]]] | None = None,
) -> EvidenceAnalysisResult:
    fetch_fn = fetcher or fetch_evidence_text
    try:
        text, source_reachable, notes = fetch_fn(source_url)
    except Exception as exc:
        text, source_reachable, notes = "", False, [f"Source unreachable: {type(exc).__name__}"]

    addr_found = address_found(address, text)
    keyword_score = keyword_match_score(scam_type, text)
    class_supported = keyword_score > 0

    if addr_found:
        notes.append("Address mentioned")
    else:
        notes.append("Address not found")

    if class_supported:
        notes.extend(build_keyword_notes(scam_type, text))
    else:
        notes.append("Classification keywords not detected")

    evidence_score = round(
        (0.5 * float(addr_found)) + (0.3 * keyword_score) + (0.2 * float(source_reachable)),
        4,
    )

    return EvidenceAnalysisResult(
        evidence_score=evidence_score,
        address_found=addr_found,
        classification_supported=class_supported,
        source_reachable=source_reachable,
        notes=notes,
    )
