from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.text_cleaner import clean_ocr_text
from app.services.filing.utils.retrieval_helpers import sort_candidates, top_n_unique


CHECKBOX_RULES = {
    "with_application": [
        (re.compile(r"\bwith\s+application\b", re.I), "true", 0.90),
        (re.compile(r"\binterlocutory\s+application\b", re.I), "true", 0.86),
        (re.compile(r"\bia\s+no\.?\b", re.I), "true", 0.82),
    ],
    "hide_party_petitioner": [],
    "hide_party_respondent": [],
    "differently_abled_petitioner": [
        (re.compile(r"\bdifferently\s+abled\b", re.I), "true", 0.86),
        (re.compile(r"\bperson\s+with\s+disability\b", re.I), "true", 0.86),
        (re.compile(r"\bdivyang\b", re.I), "true", 0.82),
    ],
    "differently_abled_respondent": [
        (re.compile(r"\bdifferently\s+abled\b", re.I), "true", 0.86),
        (re.compile(r"\bperson\s+with\s+disability\b", re.I), "true", 0.86),
        (re.compile(r"\bdivyang\b", re.I), "true", 0.82),
    ],
}


class CheckboxExtractor(BaseFieldExtractor):
    def __init__(self, field_key: str) -> None:
        self.field_key = field_key

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []
        rules = CHECKBOX_RULES.get(self.field_key, [])

        if not rules:
            return []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue

            for pattern, value, conf in rules:
                match = pattern.search(text[:6000])
                if match:
                    candidates.append(
                        {
                            "value": value,
                            "normalized_value": value,
                            "confidence": conf,
                            "source_type": "regex",
                            "page_from": page_no,
                            "page_to": page_no,
                            "chunk_id": None,
                            "evidence_text": match.group(0),
                        }
                    )

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue

            for pattern, value, conf in rules:
                match = pattern.search(text[:1500])
                if match:
                    candidates.append(
                        {
                            "value": value,
                            "normalized_value": value,
                            "confidence": conf - 0.08,
                            "source_type": "vector_retrieval",
                            "page_from": chunk.get("page_no"),
                            "page_to": chunk.get("page_no"),
                            "chunk_id": chunk.get("chunk_id"),
                            "evidence_text": match.group(0),
                        }
                    )

        candidates = sort_candidates(candidates)
        return top_n_unique(candidates, key="normalized_value", n=3)
