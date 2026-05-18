from __future__ import annotations

from app.data.case_type_master import CASE_TYPE_OPTIONS
from app.data.special_case_master import SPECIAL_CASE_OPTIONS, PARTY_NAME_SUFFIX_OPTIONS
from app.data.list_type_master import LIST_TYPE_OPTIONS
from app.data.party_detail_masters import (
    RELATION_OPTIONS,
    GENDER_OPTIONS,
    IDENTITY_PROOF_OPTIONS,
    CASTE_OPTIONS,
    STATE_OPTIONS,
    DISTRICT_OPTIONS,
    TEHSIL_OPTIONS,
    VILLAGE_OPTIONS,
)
from app.schemas.master_data import MasterListResponse, LinkedMasterListResponse, MasterOption, LinkedMasterOption


class MasterDataService:
    def _simple(self, items: list[dict]) -> MasterListResponse:
        return MasterListResponse(items=[MasterOption(**item) for item in items])

    def _linked(self, items: list[dict]) -> LinkedMasterListResponse:
        return LinkedMasterListResponse(items=[LinkedMasterOption(**item) for item in items])

    def get_case_types(self) -> MasterListResponse:
        return self._simple(CASE_TYPE_OPTIONS)

    def get_special_cases(self) -> MasterListResponse:
        return self._simple(SPECIAL_CASE_OPTIONS)

    def get_party_name_suffixes(self) -> MasterListResponse:
        return self._simple(PARTY_NAME_SUFFIX_OPTIONS)

    def get_list_types(self) -> MasterListResponse:
        return self._simple(LIST_TYPE_OPTIONS)

    def get_relations(self) -> MasterListResponse:
        return self._simple(RELATION_OPTIONS)

    def get_genders(self) -> MasterListResponse:
        return self._simple(GENDER_OPTIONS)

    def get_identity_proofs(self) -> MasterListResponse:
        return self._simple(IDENTITY_PROOF_OPTIONS)

    def get_castes(self) -> MasterListResponse:
        return self._simple(CASTE_OPTIONS)

    def get_states(self) -> MasterListResponse:
        return self._simple(STATE_OPTIONS)

    def get_districts(self, state_code: str | None = None) -> LinkedMasterListResponse:
        items = DISTRICT_OPTIONS
        if state_code:
            items = [x for x in items if x["state_code"] == state_code]
        return self._linked(items)

    def get_tehsils(self, district_code: str | None = None) -> LinkedMasterListResponse:
        items = TEHSIL_OPTIONS
        if district_code:
            items = [x for x in items if x["district_code"] == district_code]
        return self._linked(items)

    def get_villages(self, tehsil_code: str | None = None) -> LinkedMasterListResponse:
        items = VILLAGE_OPTIONS
        if tehsil_code:
            items = [x for x in items if x["tehsil_code"] == tehsil_code]
        return self._linked(items)
