from __future__ import annotations

import re

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
from app.schemas.field_quality import FieldQualityResult


class FieldQualityGateService:
    BAD_TOKENS = {
        "about:blank",
        "penal code",
        "criminal law",
        "procedure",
        "section",
        "heading/category",
        "category/sub-category",
        "subject heading",
        "subject",
        "family matters",
        "guardians and wards act",
        "wards act",
        "court fee",
        "report",
        "checker",
        "provision of law",
        "description of relief",
        "particulars of crime",
        "particulars of impugned order",
        "name of the judge",
        "objector/complainant",
        "bharatiya nagarik suraksha",
        "bhartiya nyaya sanhita",
    }

    STOPWORD_VALUES = {"and", "or", "the", "of", "in", "a", "an", "-", "."}
    PARTY_CLEANABLE_BAD_TOKENS = {
        "criminal law",
        "penal code",
        "procedure",
        "section",
    }

    VALID_RELATION_ALIASES = {
        "s/o": "S/o",
        "son of": "S/o",
        "d/o": "D/o",
        "daughter of": "D/o",
        "w/o": "W/o",
        "wife of": "W/o",
        "c/o": "C/o",
        "care of": "C/o",
        "father": "Father",
        "mother": "Mother",
        "husband": "Husband",
        "guardian": "Guardian",
    }

    VALID_GENDER_ALIASES = {"male": "Male", "female": "Female", "other": "Other"}

    STATE_ALIASES = {
        "madhya pradesh": "MP",
        "state of madhya pradesh": "MP",
        "of madhya pradesh": "MP",
        "mp": "MP",
        "m.p.": "MP",
        "uttar pradesh": "UP",
        "rajasthan": "RJ",
        "maharashtra": "MH",
        "delhi": "DL",
        "haryana": "HR",
        "punjab": "PB",
        "chandigarh": "CH",
    }

    EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
    PINCODE_RE = re.compile(r"^\d{6}$")
    DOB_RE = re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$")
    OCR_GARBAGE_RE = re.compile(r"[|~`_]{2,}")

    def __init__(self) -> None:
        self.list_type_codes = {x["code"] for x in LIST_TYPE_OPTIONS}
        self.relation_codes = {x["code"] for x in RELATION_OPTIONS}
        self.gender_codes = {x["code"] for x in GENDER_OPTIONS}
        self.state_codes = {x["code"] for x in STATE_OPTIONS}
        self.state_label_to_code = {x["label"].lower(): x["code"] for x in STATE_OPTIONS}
        self.district_codes = {x["code"] for x in DISTRICT_OPTIONS}
        self.district_label_to_code = {x["label"].lower(): x["code"] for x in DISTRICT_OPTIONS}
        self.tehsil_codes = {x["code"] for x in TEHSIL_OPTIONS}
        self.tehsil_label_to_code = {x["label"].lower(): x["code"] for x in TEHSIL_OPTIONS}
        self.village_codes = {x["code"] for x in VILLAGE_OPTIONS}
        self.village_label_to_code = {x["label"].lower(): x["code"] for x in VILLAGE_OPTIONS}
        self.caste_codes = {x["code"] for x in CASTE_OPTIONS}
        self.caste_label_to_code = {x["label"].lower(): x["code"] for x in CASTE_OPTIONS}
        self.identity_codes = {x["code"] for x in IDENTITY_PROOF_OPTIONS}
        self.identity_label_to_code = {x["label"].lower(): x["code"] for x in IDENTITY_PROOF_OPTIONS}

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        out = str(value).replace("\n", " ").strip()
        out = re.sub(r"\s{2,}", " ", out)
        out = out.strip(" |,:;")
        return out or None

    def _has_bad_token(self, value: str | None) -> str | None:
        if not value:
            return None
        low = value.lower()
        for token in self.BAD_TOKENS:
            if token in low:
                return token
        return None

    def _symbol_ratio(self, value: str) -> float:
        symbols = len(re.findall(r"[^A-Za-z0-9\s./@()&-]", value))
        return symbols / max(len(value), 1)

    def _reject(self, field_key: str, original: str | None, reason: str, penalty: float = 0.35) -> FieldQualityResult:
        return FieldQualityResult(
            field_key=field_key,
            original_value=original,
            cleaned_value=None,
            status="rejected",
            reason=reason,
            confidence_penalty=penalty,
        )

    def _accept(self, field_key: str, original: str | None, cleaned: str | None, status: str = "accepted") -> FieldQualityResult:
        return FieldQualityResult(
            field_key=field_key,
            original_value=original,
            cleaned_value=cleaned,
            status=status,
            reason=None,
            confidence_penalty=0.0 if status == "accepted" else 0.05,
        )

    def validate(self, field_key: str, value: str | None) -> FieldQualityResult:
        original = value
        cleaned = self._clean(value)

        if not cleaned:
            return FieldQualityResult(
                field_key=field_key,
                original_value=original,
                cleaned_value=None,
                status="skipped",
                reason="empty",
                confidence_penalty=0.0,
            )

        low = cleaned.lower().strip()
        if low in self.STOPWORD_VALUES:
            return self._reject(field_key, original, "stopword_value")

        if self.OCR_GARBAGE_RE.search(cleaned):
            return self._reject(field_key, original, "ocr_garbage")

        if self._symbol_ratio(cleaned) > 0.18:
            return self._reject(field_key, original, "high_symbol_ratio")

        bad_token = self._has_bad_token(cleaned)
        if bad_token:
            if field_key in {"respondent_name", "petitioner_name"}:
                party_cleaned = self.clean_party_name(cleaned)
                if party_cleaned:
                    return self.validate_party_name(field_key, original, party_cleaned)
            return self._reject(field_key, original, f"bad_token:{bad_token}")

        if field_key in {"petitioner_name", "respondent_name"}:
            return self.validate_party_name(field_key, original, cleaned)
        if field_key in {"age", "petitioner_age", "respondent_age"}:
            return self.validate_age(field_key, original, cleaned)
        if field_key in {"relation", "petitioner_relation", "respondent_relation"}:
            return self.validate_relation(field_key, original, cleaned)
        if field_key in {
            "father_or_husband",
            "petitioner_father_or_husband",
            "respondent_father_or_husband",
            "occupation",
            "petitioner_occupation",
            "respondent_occupation",
            "district",
            "petitioner_district",
            "respondent_district",
            "tehsil",
            "petitioner_tehsil",
            "respondent_tehsil",
            "village",
            "petitioner_village",
            "respondent_village",
        }:
            return self.validate_short_text(field_key, original, cleaned)
        if field_key == "date_of_birth":
            return self.validate_dob(original, cleaned)
        if field_key == "pincode":
            return self.validate_pincode(original, cleaned)
        if field_key == "phone_mobile":
            return self.validate_mobile(original, cleaned)
        if field_key == "email_id":
            return self.validate_email(original, cleaned)
        if field_key == "gender":
            return self.validate_gender(original, cleaned)
        if field_key == "country":
            return self.validate_country(original, cleaned)
        if field_key == "state":
            return self.validate_state(original, cleaned)
        if field_key in {"district", "tehsil", "village"}:
            return self.validate_location(field_key, original, cleaned)
        if field_key == "caste":
            return self.validate_caste(original, cleaned)
        if field_key == "identity_proof":
            return self.validate_identity_proof(original, cleaned)
        if field_key in {"address", "identity_proof"}:
            return self.validate_generic_text(field_key, original, cleaned)
        if field_key == "case_type":
            return self.validate_case_type(original, cleaned)
        if field_key == "list_type":
            return self.validate_list_type(original, cleaned)
        if field_key in {"special_case"}:
            return self.validate_generic_short(field_key, original, cleaned)
        if field_key.startswith("advocate_"):
            return self.validate_advocate(field_key, original, cleaned)

        return self._accept(field_key, original, cleaned)

    def clean_party_name(self, value: str) -> str | None:
        out = self._clean(value)
        if not out:
            return None

        out = out.replace("about:blank", " ")

        # Remove common OCR/source prefixes.
        out = re.sub(r"\[[A-Z0-9\-]+\]", " ", out)
        out = re.sub(r"^\s*(SCANNED|SCANED)\s+", "", out, flags=re.I)
        out = re.sub(r"^\s*\d+\s+of\s+\|?\s*", "", out, flags=re.I)
        out = re.sub(r"^\s*(GD|OD|YO|ZZ|_|~|>)+\s*", "", out, flags=re.I)

        # Strong state normalization.
        if "state of madhya pradesh" in out.lower() or "state ofmadhya pradesh" in out.lower():
            return "THE STATE OF MADHYA PRADESH"

        suffix_patterns = [
            r"\bSubject\s*Heading\b.*$",
            r"\bSubject\b.*$",
            r"\(\s*\d+\s*\)\s*CRIMINAL LAW.*$",
            r"\bCRIMINAL LAW\b.*$",
            r"\bPROCEDURE[-\d /A-Za-z.]*.*$",
            r"\bHeading/Category/Sub-Category\b.*$",
            r"\bCategory/Sub-Category\b.*$",
            r"\bProvision of law\b.*$",
            r"\bAct\s*/\s*Section\b.*$",
            r"\bSECTION\b.*$",
            r"\bParticulars of Crime\b.*$",
            r"\bParticulars of Impugned Order\b.*$",
            r"\bName\s*of\s*the\s*Judge\b.*$",
            r"\bOffence\s*u/s\b.*$",
            r"\bIN THE HIGH COURT.*$",
        ]

        for pattern in suffix_patterns:
            out = re.sub(pattern, "", out, flags=re.I)

        out = re.sub(r"\s{2,}", " ", out).strip(" |,:;-'\"[]()")

        if not out:
            return None

        return out

    def validate_party_name(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        clipped = self.clean_party_name(cleaned)

        if not clipped:
            return self._reject(field_key, original, "empty_after_party_cleanup")

        low = clipped.lower()

        illegal_fragments = [
            "high court",
            "principal seat",
            "m.cr.c",
            "mcrc",
            "cause title",
            "particulars",
            "crime no",
            "police station",
            "offence",
            "section",
            "procedure",
            "criminal law",
            "subject",
            "category",
            "act / section",
            "provision of law",
        ]

        if any(x in low for x in illegal_fragments):
            return self._reject(field_key, original, "party_name_contains_document_noise")

        if len(clipped) > 80:
            return self._reject(field_key, original, "party_name_too_long")

        if len(clipped.split()) > 8:
            return self._reject(field_key, original, "party_name_too_many_tokens")

        if self._symbol_ratio(clipped) > 0.08:
            return self._reject(field_key, original, "party_name_symbol_noise")

        return self._accept(
            field_key,
            original,
            clipped,
            "cleaned" if clipped != cleaned else "accepted",
        )

    def is_value_noisy(self, field_key: str, value: str | None) -> bool:
        result = self.validate(field_key, value)
        return result.status == "rejected"
    def validate_age(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        value = re.sub(r"\D", "", cleaned or "")
        if not value:
            return self._reject(field_key, original, "empty_age")

        age = int(value)
        if age <= 0 or age >= 120:
            return self._reject(field_key, original, "invalid_age")

        return self._accept(field_key, original, str(age), "cleaned")

    def validate_relation(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        value = (cleaned or "").strip().lower().replace(".", "")

        if value in {"s/o", "so", "son of"}:
            return self._accept(field_key, original, "S/o", "cleaned")
        if value in {"w/o", "wo", "wife of"}:
            return self._accept(field_key, original, "W/o", "cleaned")
        if value in {"d/o", "do", "daughter of"}:
            return self._accept(field_key, original, "D/o", "cleaned")

        return self._reject(field_key, original, "unknown_relation")

    def validate_short_text(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        value = self._clean(cleaned)
        if not value:
            return self._reject(field_key, original, "empty_value")

        bad = ["criminal law", "procedure", "subject heading", "provision of law", "act / section"]
        if any(token in value.lower() for token in bad):
            return self._reject(field_key, original, "document_noise")

        if len(value) > 120:
            return self._reject(field_key, original, "value_too_long")

        return self._accept(field_key, original, value, "accepted")

    def validate_relation_legacy(self, original: str | None, cleaned: str) -> FieldQualityResult:
        low = cleaned.lower().replace(".", "").strip()
        for raw, norm in self.VALID_RELATION_ALIASES.items():
            if low == raw.replace(".", ""):
                return self._accept("relation", original, norm, "cleaned")
        if cleaned in self.relation_codes:
            return self._accept("relation", original, cleaned)
        return self._reject("relation", original, "invalid_relation")

    def validate_age_legacy(self, original: str | None, cleaned: str) -> FieldQualityResult:
        if not cleaned.isdigit():
            return self._reject("age", original, "age_not_numeric")

        age = int(cleaned)

        # Single-digit ages are very likely OCR noise in filing-party text.
        if age < 10:
            return self._reject("age", original, "age_too_low_likely_ocr_noise")

        if age > 120:
            return self._reject("age", original, "age_out_of_range")

        return self._accept("age", original, cleaned)

    def validate_dob(self, original: str | None, cleaned: str) -> FieldQualityResult:
        if not self.DOB_RE.fullmatch(cleaned):
            return self._reject("date_of_birth", original, "invalid_dob")
        return self._accept("date_of_birth", original, cleaned)

    def validate_pincode(self, original: str | None, cleaned: str) -> FieldQualityResult:
        digits = re.sub(r"\D", "", cleaned)
        if not self.PINCODE_RE.fullmatch(digits):
            return self._reject("pincode", original, "invalid_pincode")
        return self._accept("pincode", original, digits, "cleaned" if digits != cleaned else "accepted")

    def validate_mobile(self, original: str | None, cleaned: str) -> FieldQualityResult:
        digits = re.sub(r"\D", "", cleaned)
        if not self.MOBILE_RE.fullmatch(digits):
            return self._reject("phone_mobile", original, "invalid_mobile")
        return self._accept("phone_mobile", original, digits, "cleaned" if digits != cleaned else "accepted")

    def validate_email(self, original: str | None, cleaned: str) -> FieldQualityResult:
        if not self.EMAIL_RE.fullmatch(cleaned):
            return self._reject("email_id", original, "invalid_email")
        return self._accept("email_id", original, cleaned)

    def validate_gender(self, original: str | None, cleaned: str) -> FieldQualityResult:
        low = cleaned.lower().strip()
        if low not in self.VALID_GENDER_ALIASES:
            return self._reject("gender", original, "invalid_gender")
        if low == "other":
            return self._reject("gender", original, "gender_other_requires_explicit_manual_review")
        return self._accept("gender", original, self.VALID_GENDER_ALIASES[low], "cleaned")

    def validate_country(self, original: str | None, cleaned: str) -> FieldQualityResult:
        if not cleaned:
            return FieldQualityResult(
                field_key="country",
                original_value=original,
                cleaned_value=None,
                status="skipped",
                reason="empty",
                confidence_penalty=0.0,
            )

        if cleaned.lower() != "india":
            return self._reject("country", original, "unsupported_country")
        return self._accept("country", original, "India", "cleaned")

    def validate_state(self, original: str | None, cleaned: str) -> FieldQualityResult:
        low = cleaned.lower().strip()
        if cleaned in self.state_codes:
            return self._accept("state", original, cleaned)
        if low in self.state_label_to_code:
            return self._accept("state", original, self.state_label_to_code[low], "cleaned")
        if low in self.STATE_ALIASES:
            return self._accept("state", original, self.STATE_ALIASES[low], "cleaned")
        return self._reject("state", original, "unknown_state")

    def validate_location(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        if len(cleaned) < 3:
            return self._reject(field_key, original, "location_too_short")
        if cleaned.lower() in self.STOPWORD_VALUES:
            return self._reject(field_key, original, "invalid_location_stopword")
        if self._has_bad_token(cleaned):
            return self._reject(field_key, original, "location_contains_legal_noise")
        if re.search(r"\d{3,}", cleaned):
            return self._reject(field_key, original, "location_contains_long_number")
        low = cleaned.lower()
        if field_key == "district":
            if cleaned in self.district_codes:
                return self._accept(field_key, original, cleaned)
            if low in self.district_label_to_code:
                return self._accept(field_key, original, self.district_label_to_code[low], "cleaned")
            return self._reject(field_key, original, "unknown_district")
        if field_key == "tehsil":
            if cleaned in self.tehsil_codes:
                return self._accept(field_key, original, cleaned)
            if low in self.tehsil_label_to_code:
                return self._accept(field_key, original, self.tehsil_label_to_code[low], "cleaned")
            return self._reject(field_key, original, "unknown_tehsil")
        if field_key == "village":
            if cleaned in self.village_codes:
                return self._accept(field_key, original, cleaned)
            if low in self.village_label_to_code:
                return self._accept(field_key, original, self.village_label_to_code[low], "cleaned")
            return self._reject(field_key, original, "unknown_village")
        return self._accept(field_key, original, cleaned)

    def validate_caste(self, original: str | None, cleaned: str) -> FieldQualityResult:
        low = cleaned.lower()
        blocked = {
            "amount awarded",
            "motor vehicle act",
            "penal code",
            "criminal law",
            "act",
            "section",
            "procedure",
            "award",
            "compensation",
            "relief",
            "injury",
            "bail",
        }
        if any(token in low for token in blocked):
            return self._reject("caste", original, "caste_contains_legal_or_award_noise")
        if len(cleaned) < 2 or len(cleaned) > 40:
            return self._reject("caste", original, "invalid_caste_length")
        if cleaned in self.caste_codes:
            return self._accept("caste", original, cleaned)
        if low in self.caste_label_to_code:
            return self._accept("caste", original, self.caste_label_to_code[low], "cleaned")
        return self._reject("caste", original, "unknown_caste")

    def validate_case_type(self, original: str | None, cleaned: str) -> FieldQualityResult:
        if len(cleaned) > 20:
            return self._reject("case_type", original, "case_type_too_long")
        if self._has_bad_token(cleaned):
            return self._reject("case_type", original, "case_type_contains_noise")
        return self._accept("case_type", original, cleaned.upper(), "cleaned")

    def validate_list_type(self, original: str | None, cleaned: str) -> FieldQualityResult:
        up = cleaned.upper()
        if up in self.list_type_codes:
            return self._accept("list_type", original, up, "cleaned")
        return self._reject("list_type", original, "unknown_list_type")

    def validate_identity_proof(self, original: str | None, cleaned: str) -> FieldQualityResult:
        up = cleaned.upper()
        low = cleaned.lower()
        if up in self.identity_codes:
            return self._accept("identity_proof", original, up, "cleaned")
        if low in self.identity_label_to_code:
            return self._accept("identity_proof", original, self.identity_label_to_code[low], "cleaned")
        return self._reject("identity_proof", original, "unknown_identity_proof")

    def validate_generic_short(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        if len(cleaned) > 60:
            return self._reject(field_key, original, "value_too_long")
        if self._has_bad_token(cleaned):
            return self._reject(field_key, original, "value_contains_noise")
        return self._accept(field_key, original, cleaned)

    def validate_generic_text(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        bad = self._has_bad_token(cleaned)
        if bad:
            return self._reject(field_key, original, f"generic_contains_noise:{bad}")
        if field_key == "address":
            low = cleaned.lower()
            blocked = [
                "objector/complainant",
                "provision of law",
                "subject",
                "category",
                "offence",
                "crime no",
                "police station",
            ]
            if any(token in low for token in blocked):
                return self._reject(field_key, original, "address_contains_case_metadata")
        if len(cleaned) > 180:
            return self._reject(field_key, original, "generic_too_long")
        return self._accept(field_key, original, cleaned)

    def validate_advocate(self, field_key: str, original: str | None, cleaned: str) -> FieldQualityResult:
        if cleaned.upper() in {"NAME", "DATE", "APPELLANT", "RESPONDENT", "PETITIONER"}:
            return self._reject(field_key, original, "advocate_label_junk")
        if len(cleaned) > 80:
            return self._reject(field_key, original, "advocate_value_too_long")
        if self._has_bad_token(cleaned):
            return self._reject(field_key, original, "advocate_contains_noise")
        return self._accept(field_key, original, cleaned)



