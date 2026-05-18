from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import ADVOCATE_HINT_PATTERNS, MOBILE_PATTERNS
from app.services.filing.utils.text_cleaner import clean_ocr_text, split_lines, is_junk_line
from app.services.filing.utils.retrieval_helpers import contextual_page_score, top_n_unique, sort_candidates
from app.services.filing.utils.candidate_quality import assess_generic_quality


class AdvocateMobileExtractor(BaseFieldExtractor):
    field_key = "advocate_mobile"

    def _normalize_mobile(self, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            page_types = page.get("page_types") or []
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue

            lines = split_lines(text)[:140]
            for idx, line in enumerate(lines):
                if is_junk_line(line):
                    continue
                for pattern in MOBILE_PATTERNS:
                    for match in pattern.finditer(line):
                        raw = match.group(0)
                        normalized = self._normalize_mobile(raw)
                        quality = assess_generic_quality(line)
                        window = " ".join(lines[max(0, idx - 1): idx + 2]).lower()
                        contextual_penalty = 0.0
                        if not any(h.search(window) for h in ADVOCATE_HINT_PATTERNS):
                            contextual_penalty = 0.08
                        if len(normalized) == 10:
                            candidates.append({
                                "value": normalized,
                                "normalized_value": normalized,
                                "confidence": max(
                                    0.0,
                                    (0.90 * contextual_page_score(page_no, page_types, self.field_key))
                                    - quality.penalty
                                    - contextual_penalty,
                                ),
                                "source_type": "regex",
                                "page_from": page_no,
                                "page_to": page_no,
                                "chunk_id": None,
                                "page_types": page_types,
                                "evidence_text": line,
                            })

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue
            page_types = chunk.get("page_types") or []

            lines = split_lines(text)[:70]
            for idx, line in enumerate(lines):
                if is_junk_line(line):
                    continue
                for pattern in MOBILE_PATTERNS:
                    for match in pattern.finditer(line):
                        raw = match.group(0)
                        normalized = self._normalize_mobile(raw)
                        quality = assess_generic_quality(line)
                        window = " ".join(lines[max(0, idx - 1): idx + 2]).lower()
                        contextual_penalty = 0.0
                        if not any(h.search(window) for h in ADVOCATE_HINT_PATTERNS):
                            contextual_penalty = 0.08
                        if len(normalized) == 10:
                            candidates.append({
                                "value": normalized,
                                "normalized_value": normalized,
                                "confidence": max(
                                    0.0,
                                    (0.82 * contextual_page_score(chunk.get("page_no"), page_types, self.field_key))
                                    - quality.penalty
                                    - contextual_penalty,
                                ),
                                "source_type": "vector_retrieval",
                                "page_from": chunk.get("page_no"),
                                "page_to": chunk.get("page_no"),
                                "chunk_id": chunk.get("chunk_id"),
                                "page_types": page_types,
                                "evidence_text": line,
                            })

        candidates = sort_candidates(candidates)
        return top_n_unique(candidates, key="normalized_value", n=4)
