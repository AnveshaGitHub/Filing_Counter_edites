from __future__ import annotations

import re

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.v2_extractors.base_v2_extractor import BaseV2Extractor


class PartyTypeV2Extractor(BaseV2Extractor):
    field_keys = {"petitioner_party_type", "respondent_party_type"}

    def infer_type(self, name: str) -> tuple[str, float]:
        low = name.lower()
        if any(x in low for x in ["state of madhya pradesh", "govt", "government", "collector", "police station", "department"]):
            return "State Department", 0.86
        if any(x in low for x in ["company", "limited", "corporation", "society", "trust", "bank"]):
            return "Other Organization", 0.76
        if re.search(r"^[A-Za-z .]{3,80}$", name) and len(name.split()) <= 6:
            return "Individual", 0.78
        return "Individual", 0.52

    def extract_from_party_candidates(self, party_candidates: list[FieldSpecificCandidate]) -> list[FieldSpecificCandidate]:
        out: list[FieldSpecificCandidate] = []
        for cand in party_candidates:
            if cand.field_key not in {"petitioner_name", "respondent_name"}:
                continue
            party_type, conf = self.infer_type(cand.normalized_value or cand.value)
            field_key = "petitioner_party_type" if cand.field_key == "petitioner_name" else "respondent_party_type"
            out.append(
                FieldSpecificCandidate(
                    field_key=field_key,
                    value=party_type,
                    normalized_value=party_type,
                    confidence=min(conf, cand.confidence),
                    page_no=cand.page_no,
                    page_type=cand.page_type,
                    evidence=cand.evidence,
                    extractor="party_type_v2_from_name",
                    status="suggested",
                )
            )
        return self.dedupe(out)

    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        return []
