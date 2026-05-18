from __future__ import annotations

import re

from app.services.filing.extractors.base import BaseFieldExtractor
from app.services.filing.utils.text_cleaner import clean_ocr_text


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PIN_RE = re.compile(r"\b\d{6}\b")
MOBILE_RE = re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b")


class RespondentMoreDetailsExtractor(BaseFieldExtractor):
    field_key = "respondent_more_details"

    def extract(self, context: dict) -> list[dict]:
        candidates: list[dict] = []

        for page in context.get("candidate_pages", []):
            text = clean_ocr_text(page.get("text"))
            if not text:
                continue

            email = EMAIL_RE.search(text)
            pin = PIN_RE.search(text)
            mobile = MOBILE_RE.search(text)

            if email or pin or mobile:
                candidates.append(
                    {
                        "value": {
                            "address": None,
                            "district": None,
                            "state": None,
                            "pincode": pin.group(0) if pin else None,
                            "mobile": mobile.group(0) if mobile else None,
                            "email": email.group(0) if email else None,
                        },
                        "normalized_value": None,
                        "confidence": 0.70,
                        "source_type": "regex",
                        "page_from": page.get("page_no"),
                        "page_to": page.get("page_no"),
                        "chunk_id": None,
                        "evidence_text": text[:300],
                    }
                )
                break

        return candidates
