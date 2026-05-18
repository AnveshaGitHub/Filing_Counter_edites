from __future__ import annotations

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import LIST_TYPE_PATTERNS
from app.services.filing.utils.retrieval_helpers import page_priority_score, top_n_unique
from app.services.filing.utils.text_cleaner import clean_ocr_text


class ListTypeExtractor(BaseFieldExtractor):
    field_key = "list_type"

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue
            scan_region = text[:2500]
            for pattern, mapped_value, base_conf in LIST_TYPE_PATTERNS:
                match = pattern.search(scan_region)
                if not match:
                    continue
                candidates.append({
                    "value": mapped_value,
                    "normalized_value": mapped_value,
                    "confidence": min(0.93, base_conf * page_priority_score(page_no)),
                    "source_type": "regex",
                    "page_from": page_no,
                    "page_to": page_no,
                    "chunk_id": None,
                    "evidence_text": scan_region[max(0, match.start() - 40): min(len(scan_region), match.end() + 80)],
                })

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue
            for pattern, mapped_value, base_conf in LIST_TYPE_PATTERNS:
                match = pattern.search(text[:1200])
                if not match:
                    continue
                candidates.append({
                    "value": mapped_value,
                    "normalized_value": mapped_value,
                    "confidence": min(0.88, base_conf - 0.04),
                    "source_type": "vector_retrieval",
                    "page_from": chunk.get("page_no"),
                    "page_to": chunk.get("page_no"),
                    "chunk_id": chunk.get("chunk_id"),
                    "evidence_text": text[max(0, match.start() - 40): min(len(text), match.end() + 80)],
                })

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return top_n_unique(candidates, key="normalized_value", n=5)
