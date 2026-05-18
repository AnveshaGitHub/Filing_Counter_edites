from __future__ import annotations

from app.data.case_type_master import CASE_TYPE_SET, CASE_TYPE_OPTIONS
from app.data.filing_field_masters import (
    LIST_TYPE_MASTER,
    LIST_TYPE_ALIASES,
    PARTY_TYPE_MASTER,
    PARTY_TYPE_ALIASES,
)


class FieldMasterService:
    def normalize_case_type(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip().upper()
        if value in CASE_TYPE_SET:
            return value
        return None

    def normalize_list_type(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        if value in LIST_TYPE_MASTER:
            return value
        return LIST_TYPE_ALIASES.get(value.lower())

    def normalize_party_type(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        if value in PARTY_TYPE_MASTER:
            return value
        return PARTY_TYPE_ALIASES.get(value.lower())

    def get_case_type_options(self) -> list[dict]:
        return list(CASE_TYPE_OPTIONS)

    def get_list_type_options(self) -> list[dict]:
        return list(LIST_TYPE_MASTER.values())

    def get_party_type_options(self) -> list[dict]:
        return list(PARTY_TYPE_MASTER.values())
