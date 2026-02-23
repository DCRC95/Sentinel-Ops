from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceAnalysisResult:
    evidence_score: float
    address_found: bool
    classification_supported: bool
    source_reachable: bool
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_score": self.evidence_score,
            "address_found": self.address_found,
            "classification_supported": self.classification_supported,
            "source_reachable": self.source_reachable,
            "notes": self.notes,
        }
