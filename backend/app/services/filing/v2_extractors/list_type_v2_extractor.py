from __future__ import annotations

import re

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.v2_extractors.base_v2_extractor import BaseV2Extractor


class ListTypeV2Extractor(BaseV2Extractor):
    field_keys = {"list_type"}
    allowed_page_types = {"filing_scrutiny_report", "hc_cause_title"}

    LIST_TYPES = {"REGULAR", "URGENT", "INDIVIDUAL"}

    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        page_texts = self.page_text_map(pages)
        candidates: list[FieldSpecificCandidate] = []

        for page_no, page_type, text in self.get_allowed_pages(classification, page_texts):
            scan = self.clean_space(text)[:1800]
            for list_type in self.LIST_TYPES:
                if re.search(rf"\b{list_type}\b", scan, re.I):
                    cand = self.make_candidate(
                        "list_type",
                        list_type,
                        0.83 if page_type == "filing_scrutiny_report" else 0.74,
                        page_no,
                        page_type,
                        scan[:220],
                        "list_type_v2",
                    )
                    if cand:
                        candidates.append(cand)

        return self.dedupe(candidates)[:3]
