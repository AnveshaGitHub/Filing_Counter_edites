from __future__ import annotations

import re

from app.schemas.ecourt_payload import ECourtPayload, ECourtValidationIssue


class ECourtPayloadValidationService:
    def validate(self, payload: ECourtPayload) -> list[ECourtValidationIssue]:
        issues: list[ECourtValidationIssue] = []

        if not payload.case_type_id:
            issues.append(self.err("case_type_id", "case_type_id is required or could not be resolved."))

        if not payload.petitionerDetails:
            issues.append(self.err("petitionerDetails", "At least one petitioner is required."))
        else:
            self._validate_party(payload.petitionerDetails[0], "petitionerDetails[0]", issues)

        if not payload.respondentDetails:
            issues.append(self.err("respondentDetails", "At least one respondent is required."))
        else:
            self._validate_party(payload.respondentDetails[0], "respondentDetails[0]", issues)

        self._validate_master_resolution(payload, issues)
        self._validate_advocate(payload.petitionerAdvocateDetails, "petitionerAdvocateDetails", issues)
        self._validate_advocate(payload.respondentAdvocateDetails, "respondentAdvocateDetails", issues)

        return self._dedupe(issues)

    def _validate_party(self, party, prefix: str, issues: list[ECourtValidationIssue]) -> None:
        if not party.partyname:
            issues.append(self.err(f"{prefix}.partyname", "partyname is required."))

        if not party.ind_dep:
            issues.append(self.err(f"{prefix}.ind_dep", "ind_dep party type is required."))

        if party.age and (party.age < 1 or party.age > 120):
            issues.append(self.warn(f"{prefix}.age", "age looks invalid."))

        if party.mobile and not re.fullmatch(r"[6-9]\d{9}", party.mobile):
            issues.append(self.warn(f"{prefix}.mobile", "mobile is not a valid Indian mobile."))

        if party.email and "@" not in party.email:
            issues.append(self.warn(f"{prefix}.email", "email looks invalid."))

        if party.pincode and not re.fullmatch(r"\d{6}", party.pincode):
            issues.append(self.warn(f"{prefix}.pincode", "pincode should be 6 digits."))

        if party.address and len(party.address) > 250:
            issues.append(self.warn(f"{prefix}.address", "address is too long."))

    def _validate_master_resolution(self, payload: ECourtPayload, issues: list[ECourtValidationIssue]) -> None:
        source_text = payload.extra.get("source_master_text", {}) if payload.extra else {}
        party_pairs = [
            ("petitioner", payload.petitionerDetails[0] if payload.petitionerDetails else None),
            ("respondent", payload.respondentDetails[0] if payload.respondentDetails else None),
        ]
        for side, party in party_pairs:
            if not party:
                continue
            for key, id_attr in [
                ("state", "state_id"),
                ("district", "district_id"),
                ("tehsil", "tehsil_id"),
                ("village", "village_id"),
            ]:
                field_key = f"{side}_{key}"
                if source_text.get(field_key) and not getattr(party, id_attr):
                    issues.append(
                        self.warn(
                            f"{side}Details[0].{id_attr}",
                            f"{key} text exists but official master ID could not be resolved.",
                        )
                    )

    def _validate_advocate(self, advocate, prefix: str, issues: list[ECourtValidationIssue]) -> None:
        if not advocate:
            return
        if advocate.adv_name and not advocate.advocate_id:
            issues.append(self.warn(f"{prefix}.advocate_id", "advocate name exists but advocate_id is missing."))

    def err(self, field_key: str, message: str) -> ECourtValidationIssue:
        return ECourtValidationIssue(field_key=field_key, message=message, severity="error")

    def warn(self, field_key: str, message: str) -> ECourtValidationIssue:
        return ECourtValidationIssue(field_key=field_key, message=message, severity="warning")

    def _dedupe(self, issues: list[ECourtValidationIssue]) -> list[ECourtValidationIssue]:
        seen = set()
        out = []
        for issue in issues:
            key = (issue.field_key, issue.message, issue.severity)
            if key in seen:
                continue
            seen.add(key)
            out.append(issue)
        return out
