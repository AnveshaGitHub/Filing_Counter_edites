from __future__ import annotations

from typing import Iterable, TypeVar

T = TypeVar("T")


def _norm_message(message: str) -> str:
    cleaned = (message or "").strip().lower().rstrip(".")
    cleaned = re_space(cleaned)

    if cleaned in {"case type is required", "case_type is required"}:
        return "case_type_required"
    if cleaned in {"petitioner name is required", "petitioner_name is required"}:
        return "petitioner_name_required"
    if cleaned in {"respondent name is required", "respondent_name is required"}:
        return "respondent_name_required"

    if "case type" in cleaned and "required" in cleaned:
        return "case_type_required"
    if "petitioner" in cleaned and "name" in cleaned and "required" in cleaned:
        return "petitioner_name_required"
    if "respondent" in cleaned and "name" in cleaned and "required" in cleaned:
        return "respondent_name_required"

    return cleaned


def re_space(value: str) -> str:
    while "  " in value:
        value = value.replace("  ", " ")
    return value


def dedupe_validation_issues(issues: Iterable[T]) -> list[T]:
    seen: set[tuple[str, str, str]] = set()
    output: list[T] = []

    for issue in issues:
        field_key = getattr(issue, "field_key", "") or ""
        message = getattr(issue, "message", "") or ""
        severity = getattr(issue, "severity", "") or ""
        key = (field_key.strip().lower(), _norm_message(message), severity.strip().lower())

        if key in seen:
            continue

        seen.add(key)
        output.append(issue)

    return output
