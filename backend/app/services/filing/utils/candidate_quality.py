from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.filing.utils.text_cleaner import admin_token_count, normalize_for_matching


@dataclass
class CandidateQuality:
    grade: str  # good / weak / reject
    penalty: float
    reason: str | None = None


BAD_KEYWORDS = {
    "limitation",
    "checker",
    "scrutiny",
    "report",
    "court fee",
    "process fee",
    "grand total",
    "filing section",
    "description of relief",
    "claimed",
    "online offline",
    "defaults",
    "scrutiny report of",
    "checked by",
}

NAME_BAD_KEYWORDS = {
    "firefox",
    "http",
    "menu.php",
    "checker",
    "scrutiny",
    "report",
    "court fee",
    "process fee",
    "grand total",
    "limitation",
    "defaults",
    "petition is time barred",
    "online offline fee",
    "checker 1",
    "subject heading",
    "category/sub-category",
    "class of case",
}


def digit_ratio(text: str) -> float:
    if not text:
        return 0.0
    digits = len(re.findall(r"\d", text))
    return digits / max(len(text), 1)


def punct_ratio(text: str) -> float:
    if not text:
        return 0.0
    punct = len(re.findall(r"[^A-Za-z0-9\s]", text))
    return punct / max(len(text), 1)


def contains_any_token(text: str, bad_tokens: set[str]) -> bool:
    low = str(text or "").lower()
    return any(token in low for token in bad_tokens)


def assess_generic_quality(text: str | None) -> CandidateQuality:
    if not text:
        return CandidateQuality("reject", 0.50, "empty")

    value = text.strip()
    low = normalize_for_matching(value)

    if len(value) < 2:
        return CandidateQuality("reject", 0.50, "too_short")

    if admin_token_count(value) >= 2:
        return CandidateQuality("reject", 0.40, "admin_tokens")

    for bad in BAD_KEYWORDS:
        if bad in low:
            return CandidateQuality("reject", 0.40, f"bad_keyword:{bad}")

    if digit_ratio(value) > 0.30:
        return CandidateQuality("weak", 0.15, "high_digit_ratio")

    if punct_ratio(value) > 0.18:
        return CandidateQuality("weak", 0.12, "high_punct_ratio")

    if len(value) > 220:
        return CandidateQuality("reject", 0.35, "too_long")

    if len(value) > 120:
        return CandidateQuality("weak", 0.10, "long")

    return CandidateQuality("good", 0.0, None)


def assess_name_quality(text: str | None) -> CandidateQuality:
    if not text:
        return CandidateQuality("reject", 0.50, "empty")

    value = text.strip()
    low = normalize_for_matching(value)

    if len(value) < 3:
        return CandidateQuality("reject", 0.50, "too_short")

    if len(value) > 90:
        return CandidateQuality("reject", 0.35, "too_long")

    for bad in NAME_BAD_KEYWORDS:
        if bad in low:
            return CandidateQuality("reject", 0.40, f"name_bad_keyword:{bad}")

    if digit_ratio(value) > 0.08:
        return CandidateQuality("weak", 0.10, "name_digit_ratio")

    if punct_ratio(value) > 0.10:
        return CandidateQuality("weak", 0.08, "name_punct_ratio")

    words = [word for word in re.split(r"\s+", value) if word]
    if len(words) > 8:
        return CandidateQuality("weak", 0.12, "too_many_tokens")

    return CandidateQuality("good", 0.0, None)


def assess_case_type_context(text: str | None) -> CandidateQuality:
    if not text:
        return CandidateQuality("reject", 0.50, "empty")

    low = normalize_for_matching(text)

    if (
        "w.p." in low
        or "wp no" in low
        or "writ petition was decided" in low
        or "order passed in w.p" in low
        or "disposed in" in low
        or "cited" in low
        or "referred case" in low
    ):
        return CandidateQuality("weak", 0.20, "referenced_wp_case")

    if "class of case" in low or "misc criminal case no" in low:
        return CandidateQuality("good", 0.0, "current_case_header")

    return CandidateQuality("good", 0.0, None)
