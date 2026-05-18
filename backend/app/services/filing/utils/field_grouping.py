from __future__ import annotations

from app.schemas.filing_extraction import FieldResult, FilingGroupedResult


CORE_KEYS = {
    "case_type",
    "list_type",
}

PETITIONER_KEYS = {
    "petitioner_name",
    "petitioner_party_type",
}

RESPONDENT_KEYS = {
    "respondent_name",
    "respondent_party_type",
}

CHECKBOX_KEYS = {
    "with_application",
    "hide_party_petitioner",
    "hide_party_respondent",
    "differently_abled_petitioner",
    "differently_abled_respondent",
}


def build_grouped_fields(fields: list[FieldResult]) -> FilingGroupedResult:
    grouped = FilingGroupedResult()

    for field in fields:
        if field.field_key in CORE_KEYS:
            grouped.core_fields[field.field_key] = field
        elif field.field_key in PETITIONER_KEYS:
            grouped.petitioner_fields[field.field_key] = field
        elif field.field_key in RESPONDENT_KEYS:
            grouped.respondent_fields[field.field_key] = field
        elif field.field_key in CHECKBOX_KEYS:
            grouped.checkbox_fields[field.field_key] = field

    return grouped
