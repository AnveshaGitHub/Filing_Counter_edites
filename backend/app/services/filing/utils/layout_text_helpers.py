from __future__ import annotations

import re

from app.services.filing.utils.text_cleaner import strip_inline_junk

LABEL_NAME_RE = re.compile(
    r"\b(applicant|petitioner|appellant|revisionist|respondent|non-applicant)\b",
    re.I,
)
ROLE_TRAIL_RE = re.compile(
    r"\b(applicant|petitioner|appellant|revisionist|respondent|non-applicant)\b.*$",
    re.I,
)
CHECKER_LEAD_RE = re.compile(r"^\s*checker\s*\d*\s*[:\-]?\s*", re.I)


def extract_after_label(line: str, labels: list[str]) -> str | None:
    for label in labels:
        pattern = re.compile(rf"\b{re.escape(label)}\b\s*[:\-]?\s*(.+)$", re.I)
        match = pattern.search(line)
        if match:
            value = normalize_name_candidate(match.group(1))
            return value or None
    return None


def extract_colon_value(line: str, labels: list[str]) -> str | None:
    low = line.lower()
    if ":" not in line:
        return None
    if not any(label.lower() in low for label in labels):
        return None
    value = line.split(":", 1)[1]
    value = normalize_name_candidate(value)
    return value or None


def get_cause_title_candidates(lines: list[str]) -> list[dict]:
    candidates: list[dict] = []
    party_labels = ["applicant", "petitioner", "appellant", "revisionist", "respondent", "non-applicant"]
    for idx, line in enumerate(lines[:120]):
        cleaned = normalize_name_candidate(line)
        if not cleaned:
            continue
        label_value = extract_after_label(cleaned, party_labels) or extract_colon_value(cleaned, party_labels)
        if label_value:
            label = "unknown"
            m = LABEL_NAME_RE.search(cleaned)
            if m:
                label = m.group(1).lower()
            candidates.append({"value": label_value, "label": label, "line": line, "line_index": idx})
    return candidates


def get_signature_block_candidates(lines: list[str]) -> list[dict]:
    candidates: list[dict] = []
    signature_tokens = [
        "advocate for applicant",
        "advocate for appellant",
        "advocate for petitioner",
        "counsel for applicant",
        "counsel for appellant",
        "memo of appearance",
        "name of the main advocate",
    ]
    for idx, line in enumerate(lines[:160]):
        low = line.lower()
        if not any(token in low for token in signature_tokens):
            continue
        window_idx = [idx - 1, idx, idx + 1]
        for pos in window_idx:
            if pos < 0 or pos >= len(lines):
                continue
            candidate = normalize_name_candidate(lines[pos])
            if not candidate:
                continue
            if "advocate for" in candidate.lower() or "counsel for" in candidate.lower():
                continue
            if len(candidate.split()) >= 2:
                candidates.append({"value": candidate, "line": lines[pos], "anchor_line": line, "line_index": pos})
    return candidates


def normalize_name_candidate(text: str | None) -> str:
    if not text:
        return ""
    value = strip_inline_junk(text)
    value = CHECKER_LEAD_RE.sub("", value)
    value = value.replace("(In Jail)", " ").replace("In Jail", " ")
    value = value.strip("[](){} ")
    value = re.sub(r"\s+", " ", value)
    value = ROLE_TRAIL_RE.sub("", value).strip(" -:;,")
    value = re.sub(r"\bsubject\b.*$", "", value, flags=re.I).strip(" -:;,")
    value = re.sub(r"\bname of the main advocate\b", "", value, flags=re.I).strip(" -:;,")
    return value.strip()

