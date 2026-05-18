from __future__ import annotations

import logging
import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.page_layout_analyzer import page_priority_multiplier
from app.services.filing.utils.suggestion_formatter import clip_display_text
from app.services.filing.utils.text_cleaner import clean_ocr_text

logger = logging.getLogger(__name__)


MCRC_PATTERNS = [
    re.compile(r"\bm\.?\s*cr\.?\s*c\.?\b", re.I),
    re.compile(r"\bmcrc\b", re.I),
    re.compile(r"\bmisc\.?\s*criminal\s*case\b", re.I),
]

CRA_PATTERNS = [
    re.compile(r"\bcriminal\s+appeal\b", re.I),
    re.compile(r"\bcra\b", re.I),
]

CRR_PATTERNS = [
    re.compile(r"\bcriminal\s+revision\b", re.I),
    re.compile(r"\bcrr\b", re.I),
]

CONC_PATTERNS = [
    re.compile(r"\bconc\b", re.I),
    re.compile(r"\bcontempt\s+petition\b", re.I),
    re.compile(r"\bcivil\s+contempt\b", re.I),
]

WP_PATTERNS = [
    re.compile(r"\bw\.?\s*p\.?\b", re.I),
    re.compile(r"\bwrit\s+petition\b", re.I),
]


class CaseTypeExtractor(BaseFieldExtractor):
    field_key = "case_type"

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        def add_case(
            value: str,
            base_conf: float,
            evidence_text: str,
            page_no: int | None,
            page_to: int | None,
            source_type: str,
            chunk_id: str | None,
            page_types: list[str],
            template_page: bool,
        ) -> None:
            multiplier = page_priority_multiplier(page_types, self.field_key)
            if template_page and value in {"CRA", "CRR"}:
                multiplier *= 0.45
            conf = max(0.0, min(0.99, base_conf * multiplier))
            candidates.append(
                {
                    "value": value,
                    "normalized_value": value,
                    "confidence": conf,
                    "source_type": source_type,
                    "page_from": page_no,
                    "page_to": page_to if page_to is not None else page_no,
                    "chunk_id": chunk_id,
                    "page_types": page_types,
                    "evidence_text": clip_display_text(evidence_text, 140),
                }
            )

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            page_types = page.get("page_types") or []
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue

            scan = text[:2000]
            has_real_case_no = bool(re.search(r"\b\d{3,6}\s*/\s*20\d{2}\b", scan))
            template_page = "template_case_type_page" in page_types and not has_real_case_no

            if any(pattern.search(scan) for pattern in MCRC_PATTERNS):
                add_case("MCRC", 0.86, scan, page_no, page_no, "regex", None, page_types, template_page)
            if any(pattern.search(scan) for pattern in CONC_PATTERNS):
                add_case("CONC", 0.86, scan, page_no, page_no, "regex", None, page_types, template_page)
            if any(pattern.search(scan) for pattern in CRA_PATTERNS):
                add_case("CRA", 0.72, scan, page_no, page_no, "regex", None, page_types, template_page)
            if any(pattern.search(scan) for pattern in CRR_PATTERNS):
                add_case("CRR", 0.72, scan, page_no, page_no, "regex", None, page_types, template_page)
            if any(pattern.search(scan) for pattern in WP_PATTERNS):
                add_case("WP", 0.68, scan, page_no, page_no, "regex", None, page_types, template_page)

        for row in context.get("index_rows", []):
            title = clean_ocr_text(row.get("title"))
            if not title:
                continue
            page_from = row.get("page_from")
            page_to = row.get("page_to")
            page_types = row.get("page_types") or []
            template_page = "template_case_type_page" in page_types

            if any(pattern.search(title) for pattern in MCRC_PATTERNS):
                add_case("MCRC", 0.88, title, page_from, page_to, "index_section", None, page_types, template_page)
            if any(pattern.search(title) for pattern in CONC_PATTERNS):
                add_case("CONC", 0.88, title, page_from, page_to, "index_section", None, page_types, template_page)
            if any(pattern.search(title) for pattern in CRA_PATTERNS):
                add_case("CRA", 0.74, title, page_from, page_to, "index_section", None, page_types, template_page)
            if any(pattern.search(title) for pattern in CRR_PATTERNS):
                add_case("CRR", 0.74, title, page_from, page_to, "index_section", None, page_types, template_page)
            if any(pattern.search(title) for pattern in WP_PATTERNS):
                add_case("WP", 0.70, title, page_from, page_to, "index_section", None, page_types, template_page)

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue
            page_types = chunk.get("page_types") or []
            scan = text[:1000]
            template_page = "template_case_type_page" in page_types and not bool(
                re.search(r"\b\d{3,6}\s*/\s*20\d{2}\b", scan)
            )
            page_no = chunk.get("page_no")
            chunk_id = chunk.get("chunk_id")

            if any(pattern.search(scan) for pattern in MCRC_PATTERNS):
                add_case("MCRC", 0.70, scan, page_no, page_no, "vector_retrieval", chunk_id, page_types, template_page)
            if any(pattern.search(scan) for pattern in CONC_PATTERNS):
                add_case("CONC", 0.70, scan, page_no, page_no, "vector_retrieval", chunk_id, page_types, template_page)
            if any(pattern.search(scan) for pattern in CRA_PATTERNS):
                add_case("CRA", 0.58, scan, page_no, page_no, "vector_retrieval", chunk_id, page_types, template_page)
            if any(pattern.search(scan) for pattern in CRR_PATTERNS):
                add_case("CRR", 0.58, scan, page_no, page_no, "vector_retrieval", chunk_id, page_types, template_page)
            if any(pattern.search(scan) for pattern in WP_PATTERNS):
                add_case("WP", 0.52, scan, page_no, page_no, "vector_retrieval", chunk_id, page_types, template_page)

        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        seen: set[str] = set()
        out: list[dict] = []
        for candidate in candidates:
            key = str(candidate.get("normalized_value") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(candidate)
            if len(out) >= 3:
                break

        if out:
            logger.info(
                "[EXTRACTION][case_type] top=%s",
                [
                    {
                        "value": c.get("value"),
                        "confidence": round(float(c.get("confidence", 0.0)), 3),
                        "src": c.get("source_type"),
                        "pt": c.get("page_types"),
                    }
                    for c in out
                ],
            )
        return out
