from __future__ import annotations

from datetime import datetime

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import ENROL_YEAR_PATTERNS
from app.services.filing.utils.text_cleaner import clean_ocr_text
from app.services.filing.utils.retrieval_helpers import top_n_unique, sort_candidates


class AdvocateEnrolYearExtractor(BaseFieldExtractor):
    field_key = "advocate_enrol_year"

    def _valid_year(self, value: str) -> bool:
        year = int(value)
        current = datetime.utcnow().year
        return 1950 <= year <= current

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue

            for pattern in ENROL_YEAR_PATTERNS:
                for match in pattern.finditer(text[:5000]):
                    year = match.group(1)
                    if self._valid_year(year):
                        candidates.append({
                            "value": year,
                            "normalized_value": year,
                            "confidence": 0.93,
                            "source_type": "regex",
                            "page_from": page_no,
                            "page_to": page_no,
                            "chunk_id": None,
                            "evidence_text": match.group(0),
                        })

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue

            for pattern in ENROL_YEAR_PATTERNS:
                for match in pattern.finditer(text):
                    year = match.group(1)
                    if self._valid_year(year):
                        candidates.append({
                            "value": year,
                            "normalized_value": year,
                            "confidence": 0.85,
                            "source_type": "vector_retrieval",
                            "page_from": chunk.get("page_no"),
                            "page_to": chunk.get("page_no"),
                            "chunk_id": chunk.get("chunk_id"),
                            "evidence_text": match.group(0),
                        })

        candidates = sort_candidates(candidates)
        return top_n_unique(candidates, key="normalized_value", n=4)
