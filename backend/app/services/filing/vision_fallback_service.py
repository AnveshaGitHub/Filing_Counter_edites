from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import fitz
import requests
from sqlalchemy.orm import Session

from app.models.local_test_document import LocalTestDocument
from app.models.local_test_document_page import LocalTestDocumentPage
from app.schemas.field_specific_extraction import FieldSpecificCandidate

logger = logging.getLogger(__name__)


VISION_PROMPT = """
You are extracting structured filing-counter data from one scanned Indian court filing page.
Return ONLY valid JSON. Do not include markdown.

Schema:
{
  "page_type": "cause_title|vakalatnama|scrutiny|order|lower_court|unknown",
  "case_type": "",
  "case_no": "",
  "case_year": "",
  "parties": [
    {
      "side": "petitioner|respondent",
      "party_no": "",
      "name": "",
      "relation": "",
      "father_husband_name": "",
      "age": "",
      "address": "",
      "district": "",
      "tehsil": "",
      "state": "",
      "party_type": ""
    }
  ],
  "advocates": [
    {
      "side": "petitioner|respondent",
      "name": "",
      "enrol_no": "",
      "enrol_year": "",
      "mobile": "",
      "email": ""
    }
  ],
  "lower_court": {
    "case_type": "",
    "case_no": "",
    "case_year": "",
    "district": "",
    "tehsil": "",
    "judge_name": "",
    "judge_designation": "",
    "impugned_judgment_date": "",
    "subject_law": "",
    "brief_description": ""
  },
  "uncertain_fields": [],
  "evidence": []
}

Rules:
- Use empty strings for unreadable values.
- Do not guess caste, gender, mobile, enrolment number, or dates.
- If text is too blurred, leave fields empty and add uncertainty.
- Prefer visible labels and table rows over nearby body text.
"""


class VisionFallbackService:
    """Optional local Ollama vision fallback. Disabled unless FILING_VISION_ENABLED=true."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.enabled = os.getenv("FILING_VISION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
        self.base_url = os.getenv("FILING_VISION_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("FILING_VISION_MODEL", "llama3.2-vision")
        self.max_pages = int(os.getenv("FILING_VISION_MAX_PAGES", "3"))
        self.timeout = int(os.getenv("FILING_VISION_TIMEOUT_SECONDS", "120"))
        self.render_dpi = int(os.getenv("FILING_VISION_RENDER_DPI", "180"))
        self.target_key_pages = os.getenv("FILING_VISION_TARGET_KEY_PAGES", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def extract_candidates(self, document_id: int) -> tuple[list[FieldSpecificCandidate], dict[str, Any]]:
        if not self.enabled:
            return [], {"enabled": False, "reason": "FILING_VISION_ENABLED is false"}

        doc = self.db.query(LocalTestDocument).filter(LocalTestDocument.id == document_id).first()
        if not doc or not doc.stored_path:
            return [], {"enabled": True, "reason": "document_not_found"}

        selected_pages = self._select_pages(document_id)
        if not selected_pages:
            return [], {"enabled": True, "reason": "no_pages_selected"}

        all_candidates: list[FieldSpecificCandidate] = []
        page_results: list[dict[str, Any]] = []
        for page_row in selected_pages:
            try:
                image_b64 = self._render_page_base64(Path(doc.stored_path), page_row.page_no)
                payload = self._call_ollama(image_b64)
                page_results.append({"page_no": page_row.page_no, "result": payload})
                all_candidates.extend(self._payload_to_candidates(page_row.page_no, payload))
            except Exception as exc:
                logger.exception("[VISION FALLBACK] failed document=%s page=%s", document_id, page_row.page_no)
                page_results.append({"page_no": page_row.page_no, "error": str(exc)})

        return all_candidates, {
            "enabled": True,
            "model": self.model,
            "selected_pages": [row.page_no for row in selected_pages],
            "results": page_results,
        }

    def _select_pages(self, document_id: int) -> list[LocalTestDocumentPage]:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )

        scored: list[tuple[float, LocalTestDocumentPage]] = []
        for row in rows:
            text = row.ocr_text or ""
            low = text.lower()
            confidence = row.ocr_avg_confidence if row.ocr_avg_confidence is not None else row.ocr_confidence
            score = 0.0
            key_page_score = self._key_page_score(low)
            if self.target_key_pages and key_page_score:
                score += key_page_score
            if confidence is not None and confidence < 0.72:
                score += 2.0
            if len(text.strip()) < 200:
                score += 1.0
            if any(token in low for token in ["petitioner", "respondent", "versus", "vakalatnama", "advocate", "lower court"]):
                score += 2.0
            if self._looks_garbled(text):
                score += 1.5
            if score >= 2.0:
                scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _score, row in scored]

    def _key_page_score(self, low: str) -> float:
        """Prefer vision on pages where specific form/table data is usually visible."""
        score = 0.0

        cause_title_tokens = ["petitioner", "respondent", "versus", "appellant", "non-applicant"]
        party_detail_tokens = ["father", "husband", "address", "district", "tehsil", "age", "party"]
        vakalatnama_tokens = ["vakalatnama", "advocate", "enrol", "enrollment", "bar council", "mobile", "email"]
        lower_court_tokens = ["lower court", "impugned", "judgment", "order", "case no", "court"]

        if sum(1 for token in cause_title_tokens if token in low) >= 2:
            score += 3.0
        if sum(1 for token in party_detail_tokens if token in low) >= 2:
            score += 2.0
        if sum(1 for token in vakalatnama_tokens if token in low) >= 2:
            score += 3.5
        if sum(1 for token in lower_court_tokens if token in low) >= 2:
            score += 2.0
        if re.search(r"[\u0900-\u097f]", low):
            score += 1.5

        return score

    def _looks_garbled(self, text: str) -> bool:
        if not text:
            return True
        words = re.findall(r"[A-Za-z]{3,}", text)
        if len(words) < 20:
            return True
        short_noise = sum(1 for word in words if len(set(word.lower())) <= 2)
        return short_noise / max(1, len(words)) > 0.35

    def _render_page_base64(self, pdf_path: Path, page_no: int) -> str:
        pdf = fitz.open(str(pdf_path))
        try:
            page = pdf[page_no - 1]
            zoom = self.render_dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            return base64.b64encode(pix.tobytes("png")).decode("ascii")
        finally:
            pdf.close()

    def _call_ollama(self, image_b64: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": VISION_PROMPT,
                "images": [image_b64],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json().get("response") or "{}"
        return json.loads(raw)

    def _payload_to_candidates(self, page_no: int, payload: dict[str, Any]) -> list[FieldSpecificCandidate]:
        page_type = str(payload.get("page_type") or "unknown")
        evidence = "; ".join(str(item) for item in payload.get("evidence") or [])[:300]
        candidates: list[FieldSpecificCandidate] = []

        for key in ["case_type", "case_no", "case_year"]:
            value = self._clean(payload.get(key))
            if value:
                candidates.append(self._candidate(key, value, page_no, page_type, evidence, 0.78))

        for party in payload.get("parties") or []:
            if not isinstance(party, dict):
                continue
            side = self._clean(party.get("side")).lower()
            party_no = self._clean(party.get("party_no")) or "1"
            prefix = f"party:{side}:{party_no}"
            for key, field_name in {
                "name": "name",
                "relation": "relation",
                "father_husband_name": "father_husband_name",
                "age": "age",
                "address": "address",
                "district": "district",
                "tehsil": "tehsil",
                "state": "state",
                "party_type": "party_type",
            }.items():
                value = self._clean(party.get(key))
                if value:
                    candidates.append(self._candidate(f"{prefix}:{field_name}", value, page_no, page_type, evidence, 0.74))

        for advocate in payload.get("advocates") or []:
            if not isinstance(advocate, dict):
                continue
            side = self._clean(advocate.get("side")).lower() or "petitioner"
            prefix = f"advocate:{side}:1"
            for key, field_name in {
                "name": "name",
                "enrol_no": "advocate_no",
                "enrol_year": "advocate_year",
                "mobile": "mobile",
                "email": "email",
            }.items():
                value = self._clean(advocate.get(key))
                if value:
                    candidates.append(self._candidate(f"{prefix}:{field_name}", value, page_no, page_type, evidence, 0.76))

        lower = payload.get("lower_court") or {}
        if isinstance(lower, dict):
            for key, field_name in {
                "case_type": "lower_court_case_type",
                "case_no": "lower_court_case_no",
                "case_year": "lower_court_case_year",
                "district": "lower_court_district",
                "tehsil": "lower_court_tehsil",
                "judge_name": "judge_name",
                "judge_designation": "judge_designation",
                "impugned_judgment_date": "impugned_judgment_date",
                "subject_law": "impugned_subject_law",
                "brief_description": "impugned_brief_description",
            }.items():
                value = self._clean(lower.get(key))
                if value:
                    candidates.append(self._candidate(field_name, value, page_no, page_type, evidence, 0.76))

        return candidates

    def _candidate(
        self,
        field_key: str,
        value: str,
        page_no: int,
        page_type: str,
        evidence: str,
        confidence: float,
    ) -> FieldSpecificCandidate:
        return FieldSpecificCandidate(
            field_key=field_key,
            value=value,
            normalized_value=value,
            confidence=confidence,
            page_no=page_no,
            page_type=page_type,
            evidence=evidence or value[:220],
            extractor=f"vision_ollama:{self.model}",
            status="suggested",
            validation_note="vision_candidate_review_required",
        )

    def _clean(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip(" ,.;:-")
