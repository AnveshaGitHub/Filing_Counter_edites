from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import ADVOCATE_HINT_PATTERNS, ENROL_NO_PATTERNS
from app.services.filing.utils.text_cleaner import clean_ocr_text, split_lines, is_junk_line
from app.services.filing.utils.retrieval_helpers import contextual_page_score, top_n_unique, sort_candidates
from app.services.filing.utils.candidate_quality import assess_generic_quality


class AdvocateEnrolNoExtractor(BaseFieldExtractor):
    field_key = "advocate_enrol_no"
    BAD_VALUES = {"NAME", "DATE", "PETITIONER", "RESPONDENT", "APPELLANT"}

    def _valid_enrol_no(self, value: str) -> bool:
        if len(value) < 4:
            return False
        if len(value) > 24:
            return False
        if re.fullmatch(r"[A-Za-z]{1,3}", value):
            return False
        return True

    def _add_from_lines(
        self,
        candidates: list[dict],
        lines: list[str],
        page_no: int | None,
        page_types: list[str] | None,
        source_type: str,
        chunk_id: str | None,
        base_conf: float,
    ) -> None:
        for idx, line in enumerate(lines):
            if is_junk_line(line):
                continue
            for pattern in ENROL_NO_PATTERNS:
                for match in pattern.finditer(line):
                    value = match.group(1).strip(" -:;,")
                    if value.upper() in self.BAD_VALUES:
                        continue
                    if len(value.strip()) < 4:
                        continue
                    if re.fullmatch(r"[A-Za-z]+", value.strip()) and len(value.strip()) <= 6:
                        continue
                    if not self._valid_enrol_no(value):
                        continue
                    quality = assess_generic_quality(line)
                    if quality.grade == "reject":
                        continue

                    window = " ".join(lines[max(0, idx - 1): idx + 2]).lower()
                    contextual_penalty = 0.0
                    if not any(h.search(window) for h in ADVOCATE_HINT_PATTERNS):
                        contextual_penalty = 0.08

                    candidates.append({
                        "value": value,
                        "normalized_value": value,
                        "confidence": max(
                            0.0,
                            (base_conf * contextual_page_score(page_no, page_types, self.field_key))
                            - quality.penalty
                            - contextual_penalty,
                        ),
                        "source_type": source_type,
                        "page_from": page_no,
                        "page_to": page_no,
                        "chunk_id": chunk_id,
                        "page_types": page_types or [],
                        "evidence_text": line,
                    })

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            page_types = page.get("page_types") or []
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue
            self._add_from_lines(
                candidates,
                split_lines(text)[:220],
                page_no,
                page_types,
                "regex",
                None,
                0.92,
            )

        for chunk in context.get("candidate_chunks", []):
            page_types = chunk.get("page_types") or []
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue
            self._add_from_lines(
                candidates,
                split_lines(text)[:100],
                chunk.get("page_no"),
                page_types,
                "vector_retrieval",
                chunk.get("chunk_id"),
                0.84,
            )

        candidates = sort_candidates(candidates)
        return top_n_unique(candidates, key="normalized_value", n=2)
