from __future__ import annotations

from pydantic import BaseModel, Field


class MasterOption(BaseModel):
    code: str
    label: str


class LinkedMasterOption(MasterOption):
    state_code: str | None = None
    district_code: str | None = None
    tehsil_code: str | None = None


class MasterListResponse(BaseModel):
    items: list[MasterOption] = Field(default_factory=list)


class LinkedMasterListResponse(BaseModel):
    items: list[LinkedMasterOption] = Field(default_factory=list)


CaseTypeMasterResponse = MasterListResponse
SpecialCaseMasterResponse = MasterListResponse
PartyNameSuffixResponse = MasterListResponse
