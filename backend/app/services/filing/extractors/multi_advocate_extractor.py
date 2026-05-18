from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.legal_patterns import (
    ADVOCATE_HINT_PATTERNS,
    ENROL_NO_PATTERNS,
    ENROL_YEAR_PATTERNS,
    MOBILE_PATTERNS,
)
from app.services.filing.utils.layout_text_helpers import get_signature_block_candidates
from app.services.filing.utils.text_cleaner import clean_ocr_text, split_lines, strip_inline_junk, is_junk_line
from app.services.filing.utils.retrieval_helpers import contextual_page_score, sort_candidates
from app.services.filing.utils.candidate_quality import assess_name_quality, assess_generic_quality


class MultiAdvocateExtractor(BaseFieldExtractor):
    field_key = "advocate_rows"

    def _clean_name(self, text: str) -> str:
        value = strip_inline_junk(text)
        value = re.sub(r"\badvocate\b", "", value, flags=re.I)
        value = re.sub(r"\bcounsel\b", "", value, flags=re.I)
        value = re.sub(r"\bfor the petitioner\b", "", value, flags=re.I)
        value = re.sub(r"\bfor petitioner\b", "", value, flags=re.I)
        value = re.sub(r"\bfor the applicant\b", "", value, flags=re.I)
        value = re.sub(r"\bfor applicant\b", "", value, flags=re.I)
        value = re.sub(r"\bfor the respondent\b", "", value, flags=re.I)
        value = re.sub(r"\bfor respondent\b", "", value, flags=re.I)
        value = re.sub(r"[:;,]+", " ", value)
        value = re.sub(r"\s{2,}", " ", value).strip()
        return value

    def _extract_block(
        self,
        text: str,
        page_no: int | None,
        chunk_id: str | None,
        page_types: list[str] | None,
    ) -> list[dict]:
        rows: list[dict] = []
        lines = split_lines(text)

        for item in get_signature_block_candidates(lines):
            name = self._clean_name(item["value"])
            name_quality = assess_name_quality(name)
            if name_quality.grade == "reject":
                continue
            rows.append(
                {
                    "value": {
                        "name": name or None,
                        "enrol_no": None,
                        "enrol_year": None,
                        "mobile": None,
                        "remark": None,
                    },
                    "normalized_value": None,
                    "confidence": max(
                        0.0,
                        0.90 * contextual_page_score(page_no, page_types, self.field_key) - name_quality.penalty,
                    ),
                    "source_type": "regex" if chunk_id is None else "vector_retrieval",
                    "page_from": page_no,
                    "page_to": page_no,
                    "chunk_id": chunk_id,
                    "page_types": page_types or [],
                    "evidence_text": item["anchor_line"][:400],
                }
            )

        for idx, line in enumerate(lines):
            low = line.lower()
            if is_junk_line(low):
                continue
            if not any(p.search(low) for p in ADVOCATE_HINT_PATTERNS):
                continue

            block_lines = [ln for ln in lines[idx : idx + 4] if not is_junk_line(ln)]
            if not block_lines:
                continue
            joined = " ".join(block_lines)

            name = self._clean_name(block_lines[0])
            if len(name.split()) < 2:
                for next_line in block_lines[1:3]:
                    maybe_name = self._clean_name(next_line)
                    if len(maybe_name.split()) >= 2:
                        name = maybe_name
                        break
            name_quality = assess_name_quality(name)
            if name_quality.grade == "reject":
                name = ""

            enrol_no = None
            for p in ENROL_NO_PATTERNS:
                m = p.search(joined)
                if m:
                    maybe_enrol = m.group(1).strip(" -:;,")
                    if len(maybe_enrol) >= 4 and not re.fullmatch(r"[A-Za-z]{1,3}", maybe_enrol):
                        enrol_no = maybe_enrol
                    break

            enrol_year = None
            for p in ENROL_YEAR_PATTERNS:
                m = p.search(joined)
                if m:
                    enrol_year = m.group(1)
                    break

            mobile = None
            for p in MOBILE_PATTERNS:
                m = p.search(joined)
                if m:
                    mobile = re.sub(r"\D", "", m.group(0))
                    if len(mobile) == 12 and mobile.startswith("91"):
                        mobile = mobile[2:]
                    if len(mobile) != 10:
                        mobile = None
                    break

            if not any([name, enrol_no, enrol_year, mobile]):
                continue

            context_quality = assess_generic_quality(joined)
            base_conf = 0.84
            if name_quality.grade == "weak":
                base_conf -= 0.10
            base_conf -= context_quality.penalty

            rows.append(
                {
                    "value": {
                        "name": name or None,
                        "enrol_no": enrol_no,
                        "enrol_year": enrol_year,
                        "mobile": mobile,
                        "remark": None,
                    },
                    "normalized_value": None,
                    "confidence": max(
                        0.0,
                        min(0.92, base_conf * contextual_page_score(page_no, page_types, self.field_key)),
                    ),
                    "source_type": "regex" if chunk_id is None else "vector_retrieval",
                    "page_from": page_no,
                    "page_to": page_no,
                    "chunk_id": chunk_id,
                    "page_types": page_types or [],
                    "evidence_text": joined[:400],
                }
            )

        return rows

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue
            candidates.extend(self._extract_block(text, page.get("page_no"), None, page.get("page_types") or []))

        for chunk in context.get("candidate_chunks", []):
            text = clean_ocr_text(chunk.get("text"))
            if not text:
                continue
            candidates.extend(
                self._extract_block(
                    text,
                    chunk.get("page_no"),
                    chunk.get("chunk_id"),
                    chunk.get("page_types") or [],
                )
            )

        return sort_candidates(candidates)
