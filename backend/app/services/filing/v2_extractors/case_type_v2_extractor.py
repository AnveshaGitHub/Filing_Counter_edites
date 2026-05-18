from __future__ import annotations

import re

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.v2_extractors.base_v2_extractor import BaseV2Extractor


class CaseTypeV2Extractor(BaseV2Extractor):
    field_keys = {"case_type"}
    allowed_page_types = {
        "hc_cause_title",
        "filing_scrutiny_report",
        "index_page",
        "application_petition",
    }

    CASE_CODES = [
        "MCRC", "CRA", "CRR", "WP", "WA", "FA", "MA", "CONC", "MCC", "RP", "RFA", "SA", "LPA"
    ]

    PATTERNS = [
        re.compile(r"\b(?P<code>M\.?\s*Cr\.?\s*C\.?|MCRC)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>W\.?\s*P\.?|WP)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>C\.?\s*R\.?\s*A\.?|CRA)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>C\.?\s*R\.?\s*R\.?|CRR)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>M\.?\s*A\.?|MA)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>Misc\.?\s*Appeal)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>F\.?\s*A\.?|FA)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>First\s*Appeal)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>SA|WA|CONC|MCC|RP|RFA|LPA)\s*(?:No\.?)?\s*[-:/ ]*\d{1,7}\s*[/_-]\s*\d{2,4}", re.I),
        re.compile(r"\b(?P<code>MCRC|CRA|CRR|WP|WA|FA|MA|CONC|MCC|RP|RFA|SA|LPA)[_-]\d{1,7}[_-]\d{4}\b", re.I),
    ]

    def normalize_code(self, raw: str) -> str | None:
        compact = re.sub(r"[^A-Za-z]", "", raw).upper()

        if compact in {"MCRC", "MCRCC"}:
            return "MCRC"
        if compact in {"WP", "WPC"}:
            return "WP"
        if compact == "CRA":
            return "CRA"
        if compact == "CRR":
            return "CRR"
        if compact in {"MA", "MISCAPPEAL"}:
            return "MA"
        if compact in {"FA", "FIRSTAPPEAL"}:
            return "FA"

        for code in self.CASE_CODES:
            if compact == code:
                return code

        return None

    def _is_metadata_noise_only(self, text: str) -> bool:
        low = text.lower()
        noise_hits = sum(1 for token in ["criminal law", "subject", "provision of law", "category"] if token in low)
        return noise_hits >= 2 and "in the high court" not in low and "no." not in low

    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        page_texts = self.page_text_map(pages)
        candidates: list[FieldSpecificCandidate] = []

        for page_no, page_type, text in self.get_allowed_pages(classification, page_texts):
            scan = self.clean_space(text)[:3000]
            if self._is_metadata_noise_only(scan):
                continue

            for pattern in self.PATTERNS:
                for match in pattern.finditer(scan):
                    code = self.normalize_code(match.group("code"))
                    if not code:
                        continue
                    base = 0.9 if page_type == "hc_cause_title" else 0.82
                    if page_type == "filing_scrutiny_report":
                        base = 0.8
                    cand = self.make_candidate(
                        "case_type",
                        code,
                        base,
                        page_no,
                        page_type,
                        match.group(0),
                        "case_type_v2",
                    )
                    if cand:
                        candidates.append(cand)

            for code in self.CASE_CODES:
                if re.search(rf"\b{re.escape(code)}[_-]\d{{1,7}}[_-]\d{{4}}\b", scan, re.I):
                    cand = self.make_candidate(
                        "case_type",
                        code,
                        0.86 if page_type == "hc_cause_title" else 0.84,
                        page_no,
                        page_type,
                        scan[:200],
                        "case_type_v2_filename_pattern",
                    )
                    if cand:
                        candidates.append(cand)

        return self.dedupe(candidates)[:3]
