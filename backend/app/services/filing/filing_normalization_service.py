from __future__ import annotations

import re

from app.data.filing_field_masters import BOOLEAN_TRUE_VALUES
from app.schemas.filing_payload import FilingFormPayload
from app.services.filing.field_master_service import FieldMasterService


class FilingNormalizationService:
    def __init__(self) -> None:
        self.master = FieldMasterService()

    def to_bool(self, value: str | bool | None) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in BOOLEAN_TRUE_VALUES

    def clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        value = re.sub(r"\s{2,}", " ", value).strip()
        return value or None

    def clean_mobile(self, value: str | None) -> str | None:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits if digits else None

    def clean_year(self, value: str | None) -> str | None:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        return digits[:4] if len(digits) >= 4 else None

    def normalize_payload(self, raw: dict) -> FilingFormPayload:
        raw_advocates = raw.get("advocates") or []
        advocates = []

        for row in raw_advocates:
            advocates.append(
                {
                    "adv_code": self.clean_text(row.get("adv_code") or row.get("advCode")),
                    "enrol_no": self.clean_text(row.get("enrol_no") or row.get("enrolNo")),
                    "enrol_year": self.clean_year(row.get("enrol_year") or row.get("enrolYear")),
                    "name": self.clean_text(row.get("name")),
                    "mobile": self.clean_mobile(row.get("mobile")),
                    "remark": self.clean_text(row.get("remark")),
                }
            )

        return FilingFormPayload(
            case_type=self.master.normalize_case_type(raw.get("case_type") or raw.get("caseType")),
            list_type=self.master.normalize_list_type(raw.get("list_type") or raw.get("listType")),
            with_application=self.to_bool(raw.get("with_application") or raw.get("withApplication")),
            petitioner_name=self.clean_text(raw.get("petitioner_name") or raw.get("petitionerName")),
            petitioner_party_type=self.master.normalize_party_type(
                raw.get("petitioner_party_type") or raw.get("petitionerType")
            ),
            hide_party_petitioner=self.to_bool(
                raw.get("hide_party_petitioner") or raw.get("hidePartyPetitioner")
            ),
            differently_abled_petitioner=self.to_bool(
                raw.get("differently_abled_petitioner") or raw.get("differentlyAbledPetitioner")
            ),
            respondent_name=self.clean_text(raw.get("respondent_name") or raw.get("respondentName")),
            respondent_party_type=self.master.normalize_party_type(
                raw.get("respondent_party_type") or raw.get("respondentType")
            ),
            hide_party_respondent=self.to_bool(
                raw.get("hide_party_respondent") or raw.get("hidePartyRespondent")
            ),
            differently_abled_respondent=self.to_bool(
                raw.get("differently_abled_respondent") or raw.get("differentlyAbledRespondent")
            ),
            advocates=advocates,
        )
