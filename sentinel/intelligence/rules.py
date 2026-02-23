from __future__ import annotations

CLASSIFICATION_KEYWORDS: dict[str, list[str]] = {
    "Phishing": ["phishing", "fake website", "impersonation"],
    "Rugpull": ["rug", "liquidity removed", "exit scam"],
    "PigButchering": ["romance scam", "investment scam", "pig butchering"],
    "Exchange": ["exchange", "cex", "withdrawal halted"],
    "Other": ["scam", "fraud", "abuse"],
}


def address_found(address: str, text: str) -> bool:
    return address.lower() in text.lower()


def keyword_match_score(scam_type: str, text: str) -> float:
    keywords = CLASSIFICATION_KEYWORDS.get(scam_type, [])
    if not keywords:
        return 0.0

    text_l = text.lower()
    matched = sum(1 for keyword in keywords if keyword.lower() in text_l)
    if matched == 0:
        return 0.0
    return min(1.0, matched / len(keywords))


def build_keyword_notes(scam_type: str, text: str) -> list[str]:
    keywords = CLASSIFICATION_KEYWORDS.get(scam_type, [])
    text_l = text.lower()
    notes = [f"Keyword matched: {keyword}" for keyword in keywords if keyword.lower() in text_l]
    return sorted(notes)
