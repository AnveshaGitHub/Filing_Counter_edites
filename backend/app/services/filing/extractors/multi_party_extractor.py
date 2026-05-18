from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import VERSUS_PATTERNS
from app.services.filing.utils.text_cleaner import clean_ocr_text, split_lines
from app.services.filing.utils.retrieval_helpers import sort_candidates


class MultiPartyExtractor(BaseFieldExtractor):
    def __init__(self, field_key: str, side: str) -> None:
        self.field_key = field_key
        self.side = side

    def _split_party_names(self, text: str) -> list[str]:
        parts = re.split(r",|;|\band\b|&", text, flags=re.I)
        names: list[str] = []
        for part in parts:
            value = part.strip(" -:;,")
            value = re.sub(r"\s{2,}", " ", value)
            if len(value) >= 3:
                names.append(value)
        return names

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            lines = split_lines(page.get("text"))

            for line in lines[:60]:
                cleaned = clean_ocr_text(line)
                if not cleaned:
                    continue

                for pattern in VERSUS_PATTERNS:
                    match = pattern.search(cleaned)
                    if not match:
                        continue

                    left = cleaned[: match.start()].strip()
                    right = cleaned[match.end() :].strip()

                    target = left if self.side == "petitioner" else right
                    for party_name in self._split_party_names(target):
                        candidates.append(
                            {
                                "value": party_name,
                                "normalized_value": party_name,
                                "confidence": 0.86,
                                "source_type": "regex",
                                "page_from": page_no,
                                "page_to": page_no,
                                "chunk_id": None,
                                "evidence_text": cleaned,
                            }
                        )

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue

            for line in split_lines(text)[:20]:
                for pattern in VERSUS_PATTERNS:
                    match = pattern.search(line)
                    if not match:
                        continue

                    left = line[: match.start()].strip()
                    right = line[match.end() :].strip()
                    target = left if self.side == "petitioner" else right

                    for party_name in self._split_party_names(target):
                        candidates.append(
                            {
                                "value": party_name,
                                "normalized_value": party_name,
                                "confidence": 0.78,
                                "source_type": "vector_retrieval",
                                "page_from": chunk.get("page_no"),
                                "page_to": chunk.get("page_no"),
                                "chunk_id": chunk.get("chunk_id"),
                                "evidence_text": line,
                            }
                        )

        return sort_candidates(candidates)
