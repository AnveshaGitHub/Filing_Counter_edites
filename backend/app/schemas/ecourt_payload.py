from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ECourtValidationIssue(BaseModel):
    field_key: str
    message: str
    severity: str = "error"


class ECourtAdvocatePayload(BaseModel):
    id: int = 0
    pet_res_no: int = 0
    adv_code: str | None = None
    adv: str | None = None
    adv_name: str | None = None
    advocate_enrollment_year: int | None = None
    state_id: int = 0
    display: str | None = None
    remark: str | None = None
    is_active: bool = True
    advocate_id: int = 0
    advocate_type_id: int = 0
    created_by: int = 0
    updated_by: int = 0


class ECourtPartyPayload(BaseModel):
    id: int = 0
    sr_no: int = 0
    pet_res: str | None = None
    ind_dep: str | None = None
    partysuff: str | None = None
    partyname: str | None = None
    prfhname_h: str | None = None
    partyname_h: str | None = None
    sonof: int = 0
    authcode: int = 0
    prfhname: str | None = None
    age: int = 0
    sex: str | None = None
    email: str | None = None
    mobile: str | None = None
    usercode: int = 0
    pflag: str | None = None
    deptcode: str | None = None
    sr_no_lrs: str | None = None
    address: str | None = None
    address_h: str | None = None
    pincode: str | None = None
    lrs_remark: str | None = None
    country_id: int = 0
    district_id: int = 0
    state_id: int = 0
    tehsil_id: int = 0
    village_id: int = 0
    is_active: bool = True
    is_hide_party_name: bool = False
    occupation: str | None = None
    dob: str | None = None
    nationality: str | None = None
    caste: str | None = None
    aadhar_no: str | None = None
    pancard_no: str | None = None
    passport_no: str | None = None
    fax: str | None = None
    phone_landline: str | None = None
    addr1: str | None = None
    created_by: int = 0
    updated_by: int = 0
    advocates: list[ECourtAdvocatePayload] = Field(default_factory=list)


class ECourtPayload(BaseModel):
    pet_name: str | None = None
    res_name: str | None = None
    filling_no: str | None = None
    provisional_no: str | None = None
    provisional_year: str | None = None

    pet_adv_code: str | None = None
    res_adv_code: str | None = None
    pet_adv_name: str | None = None
    res_adv_name: str | None = None
    pet_adv_enrollment: str | None = None
    res_adv_enrollment: str | None = None
    pet_adv_enrollment_year: str | None = None
    res_adv_enrollment_year: str | None = None

    case_pages: int = 0
    case_type_id: int = 0
    district_id: int = 0
    establishment_id: int = 0
    bench_id: int = 0
    case_nature_id: int = 0
    category: int = 0
    is_active: bool = True

    petitionerDetails: list[ECourtPartyPayload] = Field(default_factory=list)
    respondentDetails: list[ECourtPartyPayload] = Field(default_factory=list)
    petitionerAdvocateDetails: ECourtAdvocatePayload | None = None
    respondentAdvocateDetails: ECourtAdvocatePayload | None = None

    list_type: str | None = None
    bench_name: str | None = None
    hide_party: str | None = None
    special_case: list[int] = Field(default_factory=list)
    with_application: bool = False
    with_application_entries: list[dict[str, int]] = Field(default_factory=list)

    extra: dict[str, Any] = Field(default_factory=dict)


class ECourtPreviewResponse(BaseModel):
    document_id: int
    ready_for_ecourt: bool
    issues: list[ECourtValidationIssue] = Field(default_factory=list)
    payload: ECourtPayload
