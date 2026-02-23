from __future__ import annotations


def compute_consensus_score(matching_same_label: int, total_for_address: int) -> float:
    if total_for_address <= 0:
        return 0.0
    return matching_same_label / total_for_address


def compute_contractor_reliability(accepted: int, rejected: int) -> float:
    total = accepted + rejected
    if total <= 0:
        return 0.5
    return accepted / total


def compute_triage_priority(
    *,
    contractor_reliability: float,
    consensus_score: float,
    confidence_score: int,
) -> float:
    return round(
        (0.4 * contractor_reliability) + (0.3 * consensus_score) + (0.3 * (confidence_score / 5)),
        4,
    )
