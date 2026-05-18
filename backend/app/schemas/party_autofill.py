from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.field_quality import FieldQualityResult


class PartyAutofillField(BaseModel):
    value: str | None = None
    confidence: float | None = None
    source_page: int | None = None
    evidence: str | None = None


class PartyAutofillData(BaseModel):
    relation: PartyAutofillField = Field(default_factory=PartyAutofillField)
    father_or_husband: PartyAutofillField = Field(default_factory=PartyAutofillField)
    occupation: PartyAutofillField = Field(default_factory=PartyAutofillField)
    gender: PartyAutofillField = Field(default_factory=PartyAutofillField)
    date_of_birth: PartyAutofillField = Field(default_factory=PartyAutofillField)
    age: PartyAutofillField = Field(default_factory=PartyAutofillField)
    country: PartyAutofillField = Field(default_factory=PartyAutofillField)
    state: PartyAutofillField = Field(default_factory=PartyAutofillField)
    district: PartyAutofillField = Field(default_factory=PartyAutofillField)
    tehsil: PartyAutofillField = Field(default_factory=PartyAutofillField)
    village: PartyAutofillField = Field(default_factory=PartyAutofillField)
    phone_mobile: PartyAutofillField = Field(default_factory=PartyAutofillField)
    email_id: PartyAutofillField = Field(default_factory=PartyAutofillField)
    pincode: PartyAutofillField = Field(default_factory=PartyAutofillField)
    address: PartyAutofillField = Field(default_factory=PartyAutofillField)
    caste: PartyAutofillField = Field(default_factory=PartyAutofillField)
    identity_proof: PartyAutofillField = Field(default_factory=PartyAutofillField)
    name_suffix: PartyAutofillField = Field(default_factory=PartyAutofillField)


class PartyAutofillResponse(BaseModel):
    document_id: int
    side: str
    safe_to_apply: bool = True
    data: PartyAutofillData
    accepted_fields: list[str] = Field(default_factory=list)
    rejected_fields: list[str] = Field(default_factory=list)
    skipped_fields: list[str] = Field(default_factory=list)
    quality_results: list[FieldQualityResult] = Field(default_factory=list)
