from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.data.ecourt_master_seed import (
    CASE_TYPES,
    DISTRICTS,
    LIST_TYPES,
    PARTY_TYPES,
    RELATION_CODES,
    SPECIAL_CASES,
    STATES,
    TEHSILS,
    VILLAGES,
)


class ECourtMasterResolverService:
    def norm(self, value: str | None) -> str:
        if not value:
            return ""
        value = str(value).upper().strip()
        value = value.replace("M.P.", "MP")
        value = re.sub(r"[^A-Z0-9 ]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def fuzzy_lookup(self, value: str | None, mapping: dict[str, int], threshold: float = 0.85) -> int:
        target = self.norm(value)
        if not target:
            return 0

        best_id = 0
        best_score = 0.0

        for key, item_id in mapping.items():
            normalized_key = self.norm(key)
            if target == normalized_key:
                return item_id
            score = SequenceMatcher(None, target, normalized_key).ratio()
            if score > best_score:
                best_score = score
                best_id = item_id

        return best_id if best_score >= threshold else 0

    def resolve_case_type_id(self, value: str | None) -> int:
        return CASE_TYPES.get(self.norm(value), 0)

    def resolve_list_type(self, value: str | None) -> str | None:
        return LIST_TYPES.get(self.norm(value))

    def resolve_relation_code(self, value: str | None) -> int:
        if not value:
            return 0
        normalized = self.norm(value)
        aliases = {
            "S O": 1,
            "SON OF": 1,
            "D O": 2,
            "DAUGHTER OF": 2,
            "W O": 3,
            "WIFE OF": 3,
            "C O": 4,
            "CARE OF": 4,
        }
        if normalized in aliases:
            return aliases[normalized]
        for key, item_id in RELATION_CODES.items():
            if self.norm(key) == normalized:
                return item_id
        return 0

    def resolve_party_type(self, value: str | None) -> str | None:
        if not value:
            return None
        for key, item_id in PARTY_TYPES.items():
            if self.norm(key) == self.norm(value):
                return item_id
        return None

    def resolve_state_id(self, value: str | None) -> int:
        return STATES.get(self.norm(value), 0)

    def resolve_district_id(self, value: str | None) -> int:
        return self.fuzzy_lookup(value, DISTRICTS)

    def resolve_tehsil_id(self, value: str | None) -> int:
        return self.fuzzy_lookup(value, TEHSILS)

    def resolve_village_id(self, value: str | None) -> int:
        return self.fuzzy_lookup(value, VILLAGES)

    def resolve_special_case_ids(self, values: list[str] | str | None) -> list[int]:
        if not values:
            return []

        if isinstance(values, str):
            values = [values]

        out: list[int] = []
        for value in values:
            for key, item_id in SPECIAL_CASES.items():
                if self.norm(key) == self.norm(value):
                    out.append(item_id)
        return sorted(set(out))
