from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.field_specific_extraction import FieldSpecificCandidate


CASE_TYPES = {
    "WP",
    "WA",
    "FA",
    "MA",
    "MCC",
    "MCRC",
    "CONC",
    "CRR",
    "CRA",
    "SA",
    "RP",
    "MP",
    "AR",
}

MP_DISTRICTS = {
    "Agar Malwa",
    "Alirajpur",
    "Anuppur",
    "Ashoknagar",
    "Balaghat",
    "Barwani",
    "Betul",
    "Bhind",
    "Bhopal",
    "Burhanpur",
    "Chhatarpur",
    "Chhindwara",
    "Damoh",
    "Datia",
    "Dewas",
    "Dhar",
    "Dindori",
    "Guna",
    "Gwalior",
    "Harda",
    "Indore",
    "Jabalpur",
    "Jhabua",
    "Katni",
    "Khandwa",
    "Khargone",
    "Mandla",
    "Mandsaur",
    "Morena",
    "Narmadapuram",
    "Narsinghpur",
    "Neemuch",
    "Niwari",
    "Panna",
    "Raisen",
    "Rajgarh",
    "Ratlam",
    "Rewa",
    "Sagar",
    "Satna",
    "Sehore",
    "Seoni",
    "Shahdol",
    "Shajapur",
    "Sheopur",
    "Shivpuri",
    "Sidhi",
    "Singrauli",
    "Tikamgarh",
    "Ujjain",
    "Umaria",
    "Vidisha",
}


@dataclass(frozen=True)
class CandidateValidation:
    value: str
    normalized_value: str
    confidence: float
    status: str
    warning: str | None = None


class FilingMasterValidationService:
    """Small conservative validator before OCR/graph/vision candidates can autofill."""

    def validate_candidate(self, candidate: FieldSpecificCandidate) -> FieldSpecificCandidate:
        result = self.validate(candidate.field_key, candidate.value or "", candidate.confidence)
        return candidate.model_copy(
            update={
                "normalized_value": result.normalized_value,
                "confidence": result.confidence,
                "status": result.status,
                "validation_note": self._merge_note(candidate.validation_note, result.warning),
            }
        )

    def validate(self, field_key: str, value: str, confidence: float | None) -> CandidateValidation:
        raw = self._clean(value)
        base_conf = float(confidence or 0.0)
        if not raw:
            return CandidateValidation(raw, raw, 0.0, "rejected", "empty")

        key = field_key.lower()
        normalized = raw
        warning = None
        status = "suggested"

        if key.endswith("case_type") or key == "case_type":
            normalized = re.sub(r"[^A-Za-z]", "", raw).upper()
            if normalized not in CASE_TYPES:
                return CandidateValidation(raw, normalized, min(base_conf, 0.35), "rejected", "unknown_case_type")
            base_conf = max(base_conf, 0.85)

        elif "district" in key:
            normalized = self._title(raw)
            if normalized not in MP_DISTRICTS:
                warning = "district_not_in_master"
                base_conf = min(base_conf, 0.72)

        elif "state" in key:
            if re.search(r"\b(M\.?\s*P\.?|Madhya\s+Pradesh)\b", raw, re.I):
                normalized = "MADHYA PRADESH"
                base_conf = max(base_conf, 0.86)
            else:
                warning = "state_not_master_matched"
                base_conf = min(base_conf, 0.70)

        elif "mobile" in key or "phone" in key:
            match = re.search(r"(?<!\d)([6-9]\d{9})(?!\d)", raw)
            if not match:
                return CandidateValidation(raw, raw, min(base_conf, 0.40), "rejected", "invalid_mobile")
            normalized = match.group(1)

        elif "advocate_year" in key or "enrol_year" in key:
            match = re.search(r"\b(19\d{2}|20\d{2}|\d{2})\b", raw)
            if not match:
                return CandidateValidation(raw, raw, min(base_conf, 0.40), "rejected", "invalid_enrol_year")
            normalized = match.group(1)
            if len(normalized) == 2:
                normalized = f"20{normalized}" if int(normalized) <= 40 else f"19{normalized}"

        elif "advocate_no" in key or "enrol_no" in key:
            match = re.search(r"\b\d{1,6}\b", raw)
            if not match:
                return CandidateValidation(raw, raw, min(base_conf, 0.40), "rejected", "invalid_enrol_no")
            normalized = match.group(0)

        elif "caste" in key:
            if not re.search(r"\b(Caste|Category)\b", raw, re.I):
                return CandidateValidation(raw, raw, min(base_conf, 0.35), "rejected", "caste_requires_explicit_source")

        elif "party_type" in key or "ind_dept" in key:
            normalized = self._party_type(raw)
            base_conf = max(base_conf, 0.80)

        return CandidateValidation(
            value=raw,
            normalized_value=normalized,
            confidence=max(0.0, min(1.0, base_conf)),
            status=status,
            warning=warning,
        )

    def _party_type(self, value: str) -> str:
        low = value.lower()
        if any(token in low for token in ["state", "collector", "tehsildar", "secretary", "department", "government"]):
            return "State Department"
        if any(token in low for token in ["company", "limited", "corporation", "society", "trust", "bank"]):
            return "Other Organization"
        return "Individual"

    def _clean(self, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip(" ,.;:-")

    def _title(self, value: str) -> str:
        value = self._clean(value)
        return " ".join(part[:1].upper() + part[1:].lower() for part in value.split())

    def _merge_note(self, old: str | None, warning: str | None) -> str | None:
        if not warning:
            return old
        if old:
            return f"{old};{warning}"
        return warning
