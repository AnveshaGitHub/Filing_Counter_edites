from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.page_layout_analyzer import page_priority_multiplier
from app.services.filing.utils.suggestion_formatter import (
    clean_advocate_candidate,
    clip_display_text,
    should_reject_advocate_candidate,
)
from app.services.filing.utils.text_cleaner import split_lines


class AdvocateNameExtractor(BaseFieldExtractor):
    field_key = "advocate_name"

    SIGN_PATTERNS = [
        re.compile(r"advocate\s+for\s+applicant", re.I),
        re.compile(r"advocate\s+for\s+appellant", re.I),
        re.compile(r"counsel\s+for\s+applicant", re.I),
        re.compile(r"name\s+of\s+the\s+main\s+advocate", re.I),
    ]

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            page_no = page.get("page_no")
            text = page.get("text") or ""
            page_types = page.get("page_types") or []
            multiplier = page_priority_multiplier(page_types, self.field_key)
            lines = split_lines(text)

            for idx, line in enumerate(lines):
                if not any(pattern.search(line) for pattern in self.SIGN_PATTERNS):
                    continue

                window: list[str] = []
                if idx > 0:
                    window.append(lines[idx - 1])
                if idx > 1:
                    window.append(lines[idx - 2])
                if idx + 1 < len(lines):
                    window.append(lines[idx + 1])

                for raw in window:
                    cleaned = clean_advocate_candidate(raw)
                    if should_reject_advocate_candidate(cleaned):
                        continue
                    candidates.append(
                        {
                            "value": cleaned,
                            "normalized_value": cleaned,
                            "confidence": min(0.99, 0.80 * multiplier),
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
            if len(out) >= 2:
                break
        return out

