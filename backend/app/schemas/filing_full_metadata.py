from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocumentIndexItem(BaseModel):
    serial_no: int | None = None
    document_name: str | None = None
    page_range: str | None = None


class IAApplicationItem(BaseModel):
    ia_no: str | None = None
    annual_reg_no: str | None = None
    particular: str | None = None
    filed_by: str | None = None
    filed_date: str | None = None
    status: str | None = None


class ExtraAdvocateItem(BaseModel):
    advocate_no: str | None = None
    advocate_year: str | None = None
    advocate_name: str | None = None
    mobile: str | None = None
    email: str | None = None
    party_no: str | None = None
    type: str | None = None
    if_ag: str | None = None


class ExtraPartyItem(BaseModel):
    pet_res: str | None = None
    party_no: str | None = None
    ind_dept: str | None = None
    name: str | None = None
    relation: str | None = None
    father_husband_name: str | None = None
    sex: str | None = None
    age: str | None = None
    occupation_department: str | None = None
    address: str | None = None
    place_city: str | None = None
    state: str | None = None
    district: str | None = None
    pin: str | None = None
    phone_mobile: str | None = None
    email_id: str | None = None
    status: str | None = None


class FilingFullMetadata(BaseModel):
    high_court: str | None = None
    bench: str | None = None
    case_type: str | None = None
    case_no: str | None = None
    case_year: str | None = None
    filing_no: str | None = None
    filing_year: str | None = None
    filing_date: str | None = None
    case_title: str | None = None
    petitioner_display_name: str | None = None
    respondent_display_name: str | None = None
    category_text: str | None = None
    category_code: str | None = None
    sub_category_text: str | None = None
    sub_category_code: str | None = None
    last_hearing_status: str | None = None
    tentative_hearing_date: str | None = None
    last_order: str | None = None
    heading: str | None = None
    sub_heading: str | None = None
    listable_before: str | None = None
    judge1: str | None = None
    judge2: str | None = None
    before_not_before_judge: str | None = None
    purpose_of_listing: str | None = None
    list_directly: str | None = None
    list_connected_case: str | None = None
    statutory_information: str | None = None

    scrutiny_report_no: str | None = None
    scrutiny_case_type: str | None = None
    scrutiny_case_no: str | None = None
    scrutiny_case_year: str | None = None
    scrutiny_subject_heading: str | None = None
    scrutiny_category: str | None = None
    scrutiny_sub_category: str | None = None
    provision_of_law: str | None = None
    act: str | None = None
    section: str | None = None
    section_rule_article_regulation: str | None = None
    impugned_order_description: str | None = None
    relief_claimed_description: str | None = None
    court_fee_total: str | None = None
    filing_defects: str | None = None
    filing_section_note: str | None = None
    default_description: str | None = None

    case_nature: str | None = None
    limitation_section: str | None = None
    order_service_report: str | None = None
    date_of_order: str | None = None
    date_of_filing: str | None = None
    copying_date_applied: str | None = None
    delivery_ready_date: str | None = None
    compliance_period: str | None = None
    limitation_period: str | None = None
    limitation_days_calculated: str | None = None
    limitation_status: str | None = None
    holiday_year: str | None = None
    holiday_adjustment_days: str | None = None

    lower_court_type: str | None = None
    lower_court_cnr_no: str | None = None
    lower_court_district: str | None = None
    lower_court_tehsil: str | None = None
    lower_court_case_type: str | None = None
    lower_court_case_no: str | None = None
    lower_court_new_case_no: str | None = None
    lower_court_case_year: str | None = None
    impugned_judgment_date: str | None = None
    judge_designation: str | None = None
    judge_name: str | None = None
    police_station: str | None = None
    crime_no: str | None = None
    crime_year: str | None = None
    impugned_brief_description: str | None = None
    impugned_subject_law: str | None = None
    lower_court_document_no: str | None = None
    lower_court_document_year: str | None = None
    lower_court_ia_no: str | None = None
    lower_court_ia_particular: str | None = None
    lower_court_ia_amount: str | None = None
    lower_court_ia_filed_by: str | None = None
    lower_court_ia_status: str | None = None
    lower_court_ia_remark: str | None = None

    subject_code: str | None = None
    subject_name: str | None = None
    category_name: str | None = None
    sub_category_name: str | None = None
    rule: str | None = None
    regulation: str | None = None
    claim_amount: str | None = None
    relief_claimed: str | None = None
    fixed_for: str | None = None
    pmt_scan_vyapam: str | None = None

    total_pages_in_file: str | None = None
    petitioner_total_count: str | None = None
    respondent_total_count: str | None = None
    petitioner_main_advocate: str | None = None
    respondent_main_advocate: str | None = None
    petitioner_main_advocate_no: str | None = None
    petitioner_main_advocate_year: str | None = None
    petitioner_main_advocate_mobile: str | None = None
    petitioner_main_advocate_email: str | None = None
    respondent_main_advocate_no: str | None = None
    respondent_main_advocate_year: str | None = None
    respondent_main_advocate_mobile: str | None = None
    respondent_main_advocate_email: str | None = None

    office_report_summary: str | None = None
    bail_application_details: str | None = None

    document_index: list[DocumentIndexItem] = Field(default_factory=list)
    ia_applications: list[IAApplicationItem] = Field(default_factory=list)
    petitioner_extra_advocates: list[ExtraAdvocateItem] = Field(default_factory=list)
    respondent_extra_advocates: list[ExtraAdvocateItem] = Field(default_factory=list)
    extra_parties: list[ExtraPartyItem] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class FilingFullMetadataResponse(BaseModel):
    document_id: int
    metadata: FilingFullMetadata
