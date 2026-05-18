from __future__ import annotations

import re

from app.services.filing.utils.candidate_quality import (
    contains_any_token,
    digit_ratio,
    punct_ratio,
)

BAD_NAME_TOKENS = {
    "subject heading",
    "provision of law",
    "court fee",
    "description of relief",
    "checker",
    "report attached",
    "grand total",
    "remark",
    "bench",
    "status",
    "disposal",
    "category",
    "sub-category",
    "petition checked",
    "properly drawn",
    "duly stamped",
    "single bench",
    "about:blank",
}

BAD_ADVOCATE_TOKENS = {
    "name",
    "date",
    "petitioner",
    "appellant",
    "respondent",
    "subject category",
    "computer sheet",
    "about:blank",
}

MULTISPACE_RE = re.compile(r"\s+")


def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return MULTISPACE_RE.sub(" ", text).strip()


def _strip_common_noise(value: str) -> str:
    value = re.sub(r"^about:blank\s*", "", value, flags=re.I)
    value = re.sub(r"\bvs\.?$", "", value, flags=re.I)
    value = re.sub(r"\bversus\b$", "", value, flags=re.I)
    return normalize_space(value)


def clip_display_text(text: str, max_len: int = 60) -> str:
    value = normalize_space(text)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "..."


def _contains_bad_tokens(text: str, bad_tokens: set[str]) -> bool:
    return contains_any_token(normalize_space(text), bad_tokens)


def clean_party_name_candidate(text: str) -> str:
    value = _strip_common_noise(normalize_space(text))
    value = re.sub(r"\(In Jail\)", "", value, flags=re.I)
    value = re.sub(r"\bS/o\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bD/o\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bW/o\b.*$", "", value, flags=re.I)
    value = re.sub(r"\baged about\b.*$", "", value, flags=re.I)
    value = re.sub(r"\boccupation\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bR/o\b.*$", "", value, flags=re.I)
    value = re.sub(r"^\s*APPLICANT\s*[-:~]?\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*PETITIONER\s*[-:~]?\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*APPELLANT\s*[-:~]?\s*", "", value, flags=re.I)
    value = re.sub(r"\bRESPONDENT\b.*$", "", value, flags=re.I)
    value = _strip_common_noise(value)
    return value.strip(" -,:;|/\\._")


def clean_respondent_candidate(text: str) -> str:
    value = _strip_common_noise(normalize_space(text))
    low = value.lower()

    if "the state of madhya pradesh" in low:
        return "THE STATE OF MADHYA PRADESH"
    if "state of m.p." in low:
        return "State of M.P."

    value = re.sub(r"^\s*RESPONDENT\s*[-:~]?\s*", "", value, flags=re.I)
    value = re.sub(r"\bthrough\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bsubject heading\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bprovision of law\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bcourt fees?\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bdescription of relief\b.*$", "", value, flags=re.I)
    value = _strip_common_noise(value)
    return value.strip(" -,:;|/\\._")


def clean_advocate_candidate(text: str) -> str:
    value = _strip_common_noise(normalize_space(text))
    value = re.sub(r"^\(+", "", value)
    value = re.sub(r"\)+$", "", value)
    value = re.sub(r"\badvocate for applicant\b.*$", "", value, flags=re.I)
    value = re.sub(r"\badvocate for appellant\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bcounsel for applicant\b.*$", "", value, flags=re.I)
    value = re.sub(r"\bcounsel for appellant\b.*$", "", value, flags=re.I)
    value = re.sub(r"\badvocate\b.*$", "", value, flags=re.I)
    value = _strip_common_noise(value)
    return value.strip(" -,:;|/\\._")


def should_reject_name_candidate(text: str) -> bool:
    value = normalize_space(text)
    if not value:
        return True
    if len(value) > 80:
        return True
    if _contains_bad_tokens(value, BAD_NAME_TOKENS):
        return True
    if digit_ratio(value) > 0.12:
        return True
    if punct_ratio(value) > 0.14:
        return True
    if len(value.split()) > 8:
        return True
    return False


def should_reject_party_candidate(text: str) -> bool:
    value = normalize_space(text)
    if not value:
        return True
    if len(value) > 100:
        return True
    if _contains_bad_tokens(value, BAD_NAME_TOKENS):
        return True
    if "criminal law" in value.lower():
        return True
    if "section" in value.lower() and len(value) > 30:
        return True
    return False


def should_reject_advocate_candidate(text: str) -> bool:
    value = normalize_space(text)
    if not value:
        return True
    if value.upper() in {"NAME", "DATE", "PETITIONER", "APPELLANT", "RESPONDENT"}:
        return True
    if _contains_bad_tokens(value, BAD_ADVOCATE_TOKENS):
        return True
    if len(value) > 60:
        return True
    if len(value.split()) > 6:
        return True
    if digit_ratio(value) > 0.20:
        return True
    return False
