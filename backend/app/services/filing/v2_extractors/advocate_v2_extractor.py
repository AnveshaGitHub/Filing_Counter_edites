from __future__ import annotations

import re

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.v2_extractors.base_v2_extractor import BaseV2Extractor


class AdvocateV2Extractor(BaseV2Extractor):
    field_keys = {"advocate_name", "advocate_mobile"}
    allowed_page_types = {"memo_of_appearance", "vakalatnama", "hc_cause_title"}

    MOBILE_RE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")

    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        page_texts = self.page_text_map(pages)
        candidates: list[FieldSpecificCandidate] = []

        for page_no, page_type, text in self.get_allowed_pages(classification, page_texts):
            lines = [self.clean_space(x) for x in re.split(r"[\n\r]+", text or "")]
            lines = [x for x in lines if x]

            for idx, line in enumerate(lines):
                low = line.lower()
                has_adv_marker = any(x in low for x in ["advocate", "counsel"])

                if has_adv_marker:
                    window = []
                    if idx > 0:
                        window.append(lines[idx - 1])
                    if idx + 1 < len(lines):
                        window.append(lines[idx + 1])
                    for raw in window:
                        if len(raw) > 80:
                            continue
                        if re.search(r"\b(advocate|counsel|applicant|respondent|petitioner)\b", raw, re.I):
                            continue
                        cand = self.make_candidate(
                            "advocate_name",
                            raw.strip("() "),
                            0.74,
                            page_no,
                            page_type,
                            f"{raw} {line}",
                            "advocate_v2_signature_window",
                        )
                        if cand:
                            candidates.append(cand)

                if has_adv_marker:
                    for mobile in self.MOBILE_RE.findall(line):
                        cand = self.make_candidate(
                            "advocate_mobile",
                            mobile,
                            0.8 if page_type in {"memo_of_appearance", "vakalatnama"} else 0.66,
                            page_no,
                            page_type,
                            line[:220],
                            "advocate_v2_mobile",
                        )
                        if cand:
                            candidates.append(cand)

        return self.dedupe(candidates)[:4]
