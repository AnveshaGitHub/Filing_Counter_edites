from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.page_layout_analyzer import page_priority_multiplier
from app.services.filing.utils.suggestion_formatter import (
    clean_respondent_candidate,
    clip_display_text,
    should_reject_party_candidate,
)
from app.services.filing.utils.text_cleaner import split_lines


class RespondentNameExtractor(BaseFieldExtractor):
    field_key = "respondent_name"

    RESP_PATTERNS = [
        re.compile(r"\bRESPONDENT\b\s*[-:~]?\s*(.+)", re.I),
        re.compile(r"\b-Vs-\b\s*(.+)", re.I),
        re.compile(r"\bVERSUS\b\s*(.+)", re.I),
    ]

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            text = page.get("text") or ""
            page_types = page.get("page_types") or []
            multiplier = page_priority_multiplier(page_types, self.field_key)

            for line in split_lines(text)[:60]:
                for pattern in self.RESP_PATTERNS:
                    match = pattern.search(line)
                    if not match:
                        continue

                    raw = match.group(1)
                    cleaned = clean_respondent_candidate(raw)
                    if should_reject_party_candidate(cleaned):
                        continue

                    candidates.append(
                        {
                            "value": cleaned,
                            "normalized_value": cleaned,
                            "confidence": min(0.99, 0.78 * multiplier),
                            "source_type": "regex",
                            "page_from": page_no,
                            "page_to": page_no,
                            "chunk_id": None,
                            "page_types": page_types,
                            "evidence_text": clip_display_text(line, 140),
                        }
                    )

        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        out: list[dict] = []
        seen: set[str] = set()
        for candidate in candidates:
            value = str(candidate.get("normalized_value") or "")
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(candidate)
            if len(out) >= 3:
                break
        return out

