from __future__ import annotations

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import (
    STATE_DEPT_PATTERNS,
    CENTRAL_DEPT_PATTERNS,
    ORG_PATTERNS,
)
from app.services.filing.utils.text_cleaner import clean_ocr_text
from app.services.filing.utils.retrieval_helpers import contextual_page_score, top_n_unique, sort_candidates
from app.services.filing.utils.candidate_quality import assess_name_quality


class PartyTypeExtractor(BaseFieldExtractor):
    def __init__(self, field_key: str, linked_name_field: str) -> None:
        self.field_key = field_key
        self.linked_name_field = linked_name_field

    def _classify(self, text: str) -> tuple[str, float] | None:
        low = text.lower()
        for pattern in CENTRAL_DEPT_PATTERNS:
            if pattern.search(low):
                return ("Central Department", 0.93)

        for pattern in STATE_DEPT_PATTERNS:
            if pattern.search(low):
                return ("State Department", 0.92)

        for pattern in ORG_PATTERNS:
            if pattern.search(low):
                return ("Other Organization", 0.88)

        if text.strip():
            return ("Individual", 0.76)

        return None

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        linked_name_value = context.get("linked_name_value")
        linked_name_evidence = context.get("linked_name_evidence")

        if linked_name_value:
            name_quality = assess_name_quality(str(linked_name_value))
            classified = self._classify(linked_name_value)
            if classified:
                value, conf = classified
                if name_quality.grade == "weak":
                    conf -= 0.10
                elif name_quality.grade == "reject":
                    conf -= 0.22
                candidates.append({
                    "value": value,
                    "normalized_value": value,
                    "confidence": max(0.0, conf),
                    "source_type": "rule",
                    "page_from": linked_name_evidence.get("page_from") if linked_name_evidence else None,
                    "page_to": linked_name_evidence.get("page_to") if linked_name_evidence else None,
                    "chunk_id": linked_name_evidence.get("chunk_id") if linked_name_evidence else None,
                    "evidence_text": linked_name_value,
                })

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue
            page_types = chunk.get("page_types") or []
            classified = self._classify(text[:500])
            if classified:
                value, conf = classified
                quality = assess_name_quality(text[:120])
                candidates.append({
                    "value": value,
                    "normalized_value": value,
                    "confidence": max(
                        0.0,
                        ((conf - 0.12) * contextual_page_score(chunk.get("page_no"), page_types, self.field_key))
                        - (0.12 if quality.grade != "good" else 0.0),
                    ),
                    "source_type": "vector_retrieval",
                    "page_from": chunk.get("page_no"),
                    "page_to": chunk.get("page_no"),
                    "chunk_id": chunk.get("chunk_id"),
                    "page_types": page_types,
                    "evidence_text": text[:300],
                })

        candidates = sort_candidates(candidates)
        return top_n_unique(candidates, key="normalized_value", n=4)
