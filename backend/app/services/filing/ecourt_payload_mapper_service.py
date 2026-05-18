from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.extracted_field import ExtractedField
from app.models.extraction_job import ExtractionJob
from app.models.reviewed_filing_field import ReviewedFilingField
from app.models.reviewed_filing_session import ReviewedFilingSession
from app.schemas.ecourt_payload import ECourtAdvocatePayload, ECourtPartyPayload, ECourtPayload
from app.services.filing.ecourt_master_resolver_service import ECourtMasterResolverService

logger = logging.getLogger(__name__)


class ECourtPayloadMapperService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.resolver = ECourtMasterResolverService()

    def build(self, document_id: int) -> ECourtPayload:
        internal = self._load_internal_payload(document_id)

        case_type = self._get(internal, "case_type")
        list_type = self._get(internal, "list_type")
        special_case = self._get(internal, "special_case")
        with_application = self._to_bool(self._get(internal, "with_application"))

        petitioner = self._party_payload(internal, side="petitioner", sr_no=1)
        respondent = self._party_payload(internal, side="respondent", sr_no=1)

        petitioner_adv = self._advocate_payload(internal, side="petitioner")
        respondent_adv = self._advocate_payload(internal, side="respondent")

        if petitioner_adv:
            petitioner.advocates.append(petitioner_adv)
        if respondent_adv:
            respondent.advocates.append(respondent_adv)

        payload = ECourtPayload(
            pet_name=petitioner.partyname,
            res_name=respondent.partyname,
            case_type_id=self.resolver.resolve_case_type_id(case_type),
            list_type=self.resolver.resolve_list_type(list_type) or list_type,
            special_case=self.resolver.resolve_special_case_ids(special_case),
            with_application=with_application,
            with_application_entries=[],
            petitionerDetails=[petitioner],
            respondentDetails=[respondent],
            petitionerAdvocateDetails=petitioner_adv,
            respondentAdvocateDetails=respondent_adv,
            pet_adv_name=petitioner_adv.adv_name if petitioner_adv else None,
            res_adv_name=respondent_adv.adv_name if respondent_adv else None,
            pet_adv_code=petitioner_adv.adv_code if petitioner_adv else None,
            res_adv_code=respondent_adv.adv_code if respondent_adv else None,
            pet_adv_enrollment=petitioner_adv.adv if petitioner_adv else None,
            res_adv_enrollment=respondent_adv.adv if respondent_adv else None,
            pet_adv_enrollment_year=str(petitioner_adv.advocate_enrollment_year)
            if petitioner_adv and petitioner_adv.advocate_enrollment_year
            else None,
            res_adv_enrollment_year=str(respondent_adv.advocate_enrollment_year)
            if respondent_adv and respondent_adv.advocate_enrollment_year
            else None,
            extra={
                "source_master_text": self._source_master_text(internal),
                "source_payload_kind": internal.get("_source_payload_kind"),
            },
        )

        if payload.with_application and payload.case_type_id:
            payload.with_application_entries.append({"case_type_id": payload.case_type_id, "sub_doc_code": 0})

        return payload

    def _party_payload(self, internal: dict[str, Any], side: str, sr_no: int) -> ECourtPartyPayload:
        party_type_text = self._get(internal, f"{side}_party_type")
        state_text = self._get(internal, f"{side}_state")
        district_text = self._get(internal, f"{side}_district")
        tehsil_text = self._get(internal, f"{side}_tehsil")
        village_text = self._get(internal, f"{side}_village")

        return ECourtPartyPayload(
            sr_no=sr_no,
            pet_res="P" if side == "petitioner" else "R",
            ind_dep=self.resolver.resolve_party_type(party_type_text),
            partysuff=self._get(internal, f"{side}_name_suffix"),
            partyname=self._get(internal, f"{side}_name"),
            partyname_h=self._get(internal, f"{side}_name_regional"),
            prfhname=self._get(internal, f"{side}_father_or_husband"),
            sonof=self.resolver.resolve_relation_code(self._get(internal, f"{side}_relation")),
            age=self._int_or_zero(self._get(internal, f"{side}_age")),
            sex=self._get(internal, f"{side}_gender"),
            email=self._get(internal, f"{side}_email") or self._get(internal, f"{side}_email_id"),
            mobile=self._get(internal, f"{side}_mobile") or self._get(internal, f"{side}_phone_mobile"),
            address=self._get(internal, f"{side}_address"),
            pincode=self._get(internal, f"{side}_pincode"),
            country_id=1,
            state_id=self.resolver.resolve_state_id(state_text),
            district_id=self.resolver.resolve_district_id(district_text),
            tehsil_id=self.resolver.resolve_tehsil_id(tehsil_text),
            village_id=self.resolver.resolve_village_id(village_text),
            occupation=self._get(internal, f"{side}_occupation"),
            dob=self._get(internal, f"{side}_date_of_birth"),
            nationality=self._get(internal, f"{side}_nationality") or "INDIAN",
            caste=self._get(internal, f"{side}_caste"),
            aadhar_no=self._get(internal, f"{side}_aadhar_no"),
            pancard_no=self._get(internal, f"{side}_pancard_no"),
            passport_no=self._get(internal, f"{side}_passport_no"),
            is_hide_party_name=self._to_bool(self._get(internal, f"hide_party_{side}")),
        )

    def _advocate_payload(self, internal: dict[str, Any], side: str) -> ECourtAdvocatePayload | None:
        name = self._get(internal, f"{side}_advocate_name") or self._get(internal, "advocate_name")
        code = (
            self._get(internal, f"{side}_advocate_code")
            or self._get(internal, f"{side}_adv_code")
            or self._get(internal, "advocate_code")
            or self._get(internal, "adv_code")
        )
        enrol_no = (
            self._get(internal, f"{side}_advocate_enrol_no")
            or self._get(internal, f"{side}_advocate_enrollment")
            or self._get(internal, "advocate_enrol_no")
            or self._get(internal, "advocate_enrollment")
        )
        enrol_year = (
            self._get(internal, f"{side}_advocate_enrol_year")
            or self._get(internal, f"{side}_advocate_enrollment_year")
            or self._get(internal, "advocate_enrol_year")
            or self._get(internal, "advocate_enrollment_year")
        )
        remark = self._get(internal, f"{side}_advocate_remark") or self._get(internal, "advocate_remark")

        if not any([name, code, enrol_no, enrol_year, remark]):
            return None

        return ECourtAdvocatePayload(
            adv_code=code,
            adv=enrol_no,
            adv_name=name,
            advocate_enrollment_year=self._int_or_none(enrol_year),
            display=name,
            remark=remark,
            advocate_id=0,
            advocate_type_id=0,
        )

    def _load_internal_payload(self, document_id: int) -> dict[str, Any]:
        internal: dict[str, Any] = {"_source_payload_kind": "empty"}

        try:
            from app.services.filing.filing_payload_builder_service import FilingPayloadBuilderService

            response = FilingPayloadBuilderService(self.db).get_filing_payload(document_id)
            payload = response.payload
            if hasattr(payload, "model_dump"):
                internal.update(payload.model_dump())
            elif isinstance(payload, dict):
                internal.update(payload)
            internal["_source_payload_kind"] = "filing_payload"
        except Exception:
            logger.exception("[ECOURT PAYLOAD] failed to load internal filing payload")

        direct_fields = self._load_latest_review_fields(document_id) or self._load_latest_extraction_fields(document_id)
        internal.update(direct_fields)

        advocates = internal.get("advocates")
        if isinstance(advocates, list) and advocates:
            first_advocate = advocates[0] or {}
            if isinstance(first_advocate, dict):
                internal.setdefault("advocate_name", first_advocate.get("name"))
                internal.setdefault("advocate_code", first_advocate.get("adv_code") or first_advocate.get("advCode"))
                internal.setdefault("advocate_enrol_no", first_advocate.get("enrol_no") or first_advocate.get("enrolNo"))
                internal.setdefault(
                    "advocate_enrol_year", first_advocate.get("enrol_year") or first_advocate.get("enrolYear")
                )
                internal.setdefault("advocate_mobile", first_advocate.get("mobile"))
                internal.setdefault("advocate_remark", first_advocate.get("remark"))

        return internal

    def _load_latest_review_fields(self, document_id: int) -> dict[str, Any]:
        session = (
            self.db.query(ReviewedFilingSession)
            .filter(ReviewedFilingSession.document_id == document_id)
            .order_by(ReviewedFilingSession.id.desc())
            .first()
        )
        if not session:
            return {}

        rows = (
            self.db.query(ReviewedFilingField)
            .filter(ReviewedFilingField.reviewed_session_id == session.id)
            .all()
        )
        out: dict[str, Any] = {"_source_payload_kind": "review"}
        for row in rows:
            out[row.field_key] = row.reviewed_value if row.reviewed_value is not None else row.system_value
        return out

    def _load_latest_extraction_fields(self, document_id: int) -> dict[str, Any]:
        job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.document_id == document_id)
            .order_by(ExtractionJob.id.desc())
            .first()
        )
        if not job:
            return {}

        rows = (
            self.db.query(ExtractedField)
            .filter(ExtractedField.extraction_job_id == job.id)
            .order_by(ExtractedField.confidence.asc())
            .all()
        )
        out: dict[str, Any] = {"_source_payload_kind": "extraction"}
        for row in rows:
            value = row.normalized_value or row.raw_value
            if value is not None:
                out[row.field_key] = value
        return out

    def _source_master_text(self, internal: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "case_type",
            "list_type",
            "special_case",
            "petitioner_state",
            "petitioner_district",
            "petitioner_tehsil",
            "petitioner_village",
            "respondent_state",
            "respondent_district",
            "respondent_tehsil",
            "respondent_village",
        ]
        return {key: self._get(internal, key) for key in keys if self._get(internal, key)}

    def _get(self, data: dict[str, Any], key: str) -> Any:
        value = data.get(key)
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    def _int_or_zero(self, value: Any) -> int:
        parsed = self._int_or_none(value)
        return parsed if parsed is not None else 0

    def _int_or_none(self, value: Any) -> int | None:
        try:
            if value is None or value == "":
                return None
            return int(str(value).strip())
        except Exception:
            return None

    def _to_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)
