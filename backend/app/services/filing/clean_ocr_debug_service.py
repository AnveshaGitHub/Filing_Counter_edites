from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.local_test_document_page import LocalTestDocumentPage
from app.services.filing.field_page_router_service import FieldPageRouterService
from app.services.filing.page_classifier_service import PageClassifierService
from app.services.filing.utils.text_cleaner import clean_ocr_text


class CleanOcrDebugService:
    FIELD_KEYS = [
        "case_type",
        "list_type",
        "petitioner_name",
        "respondent_name",
        "petitioner_party_type",
        "respondent_party_type",
        "advocate_name",
        "advocate_enrol_no",
        "advocate_enrol_year",
        "advocate_mobile",
    ]

    PARTY_LABEL_RE = re.compile(
        r"\b(applicant|applicants|petitioner|petitioners|appellant|appellants|"
        r"respondent|respondents|non[-\s]?applicant|non[-\s]?applicants)\b",
        re.IGNORECASE,
    )
    PETITIONER_LABEL_RE = re.compile(
        r"\b(applicant|applicants|petitioner|petitioners|appellant|appellants)\b",
        re.IGNORECASE,
    )
    RESPONDENT_LABEL_RE = re.compile(
        r"\b(respondent|respondents|non[-\s]?applicant|non[-\s]?applicants)\b",
        re.IGNORECASE,
    )
    CASE_NUMBER_RE = re.compile(
        r"\b(?:M\.?\s*Cr\.?\s*C\.?|MCRC|W\.?\s*P\.?|WP|F\.?\s*A\.?|FA|"
        r"M\.?\s*A\.?|MA|C\.?\s*R\.?\s*A\.?|CRA|C\.?\s*R\.?\s*R\.?|CRR)"
        r"\s*(?:No\.?|Number|/|\(|\.|\s)*\s*[\w./ -]{0,30}?\d{1,6}\s*/\s*\d{4}\b",
        re.IGNORECASE,
    )
    ADVOCATE_TABLE_RE = re.compile(
        r"\b(enrol(?:l)?(?:ment)?\s*no|state\s+bar\s+council|telephone|mobile|"
        r"full\s+name|advocate|vakalatnama)\b",
        re.IGNORECASE,
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.classifier = PageClassifierService(db)
        self.router = FieldPageRouterService(db)

    def build_debug_payload(self, document_id: int) -> dict[str, Any]:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        if not rows:
            raise ValueError("local_test_document_not_processed")

        routes = self.router.get_routes(document_id).get("routes", {})
        page_route_map = self._build_page_route_map(routes)

        return {
            "document_id": document_id,
            "pages": [
                self._page_debug(row=row, route_map=page_route_map.get(row.page_no, {}))
                for row in rows
            ],
            "field_routes": {
                field_key: self._route_debug(field_key, routes.get(field_key, []))
                for field_key in self.FIELD_KEYS
            },
        }

    def _page_debug(self, row: LocalTestDocumentPage, route_map: dict[str, Any]) -> dict[str, Any]:
        raw_text = row.ocr_text or ""
        clean_lines = self._clean_lines(row)
        clean_text = "\n".join(clean_lines)
        page_classification = self.classifier.classify_text(row.page_no, clean_text or raw_text)
        quality = self._quality(clean_text or raw_text)

        return {
            "page_no": row.page_no,
            "raw_ocr_confidence": row.ocr_confidence,
            "ocr_avg_confidence": row.ocr_avg_confidence,
            "extraction_method": row.extraction_method,
            "page_type": page_classification.page_type,
            "page_type_confidence": page_classification.confidence,
            "page_type_reasons": page_classification.reasons,
            "text_length": row.text_length if row.text_length is not None else len(raw_text),
            "quality": quality,
            "clean_lines": clean_lines,
            "candidate_blocks": self._candidate_blocks(clean_lines),
            "rejected_candidate_hints": self._rejected_candidate_hints(clean_lines),
            "field_route_scores": route_map,
        }

    def _clean_lines(self, row: LocalTestDocumentPage) -> list[str]:
        raw_lines = self._layout_lines(row.ocr_lines_json)
        if not raw_lines:
            raw_lines = (row.ocr_text or "").splitlines()

        lines: list[str] = []
        seen: set[str] = set()
        for raw_line in raw_lines:
            line = self._clean_line(raw_line)
            if not line:
                continue
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            lines.append(line)
        return lines

    def _layout_lines(self, raw_json: str | None) -> list[str]:
        if not raw_json:
            return []
        try:
            items = json.loads(raw_json)
        except Exception:
            return []
        if not isinstance(items, list):
            return []
        lines: list[str] = []
        for item in items:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    lines.append(text)
        return lines

    def _clean_line(self, line: str) -> str:
        line = clean_ocr_text(line or "")
        line = line.replace("|", " | ")
        line = re.sub(r"[_·•]{2,}", " ", line)
        line = re.sub(r"\s*[-:]\s*$", ":", line)
        line = re.sub(r"\s+", " ", line)
        return line.strip(" \t\r\n")

    def _quality(self, text: str) -> dict[str, bool]:
        low = text.lower()
        return {
            "has_case_number": bool(self.CASE_NUMBER_RE.search(text)),
            "has_party_labels": bool(self.PARTY_LABEL_RE.search(text)),
            "has_petitioner_label": bool(self.PETITIONER_LABEL_RE.search(text)),
            "has_respondent_label": bool(self.RESPONDENT_LABEL_RE.search(text)),
            "has_applicant_label": "applicant" in low,
            "has_versus": bool(re.search(r"\b(versus|vs\.?|v/s)\b", low)),
            "has_advocate_table": bool(self.ADVOCATE_TABLE_RE.search(text)),
            "is_index_page": bool(re.search(r"\b(index|description of documents|annexure|page no)\b", low)),
            "is_order_page": bool(re.search(r"\b(order sheet|order or proceeding|judgment|order dated)\b", low)),
            "is_vakalatnama_page": "vakalatnama" in low,
        }

    def _candidate_blocks(self, lines: list[str]) -> dict[str, str | None]:
        return {
            "case_title": self._case_title_block(lines),
            "case_number_block": self._first_match(lines, self.CASE_NUMBER_RE),
            "petitioner_block": self._label_block(lines, self.PETITIONER_LABEL_RE),
            "respondent_block": self._label_block(lines, self.RESPONDENT_LABEL_RE),
            "advocate_block": self._advocate_block(lines),
        }

    def _case_title_block(self, lines: list[str]) -> str | None:
        selected: list[str] = []
        for line in lines:
            low = line.lower()
            if (
                "high court" in low
                or self.CASE_NUMBER_RE.search(line)
                or self.PARTY_LABEL_RE.search(line)
                or re.search(r"\b(versus|vs\.?|v/s)\b", low)
            ):
                selected.append(line)
            if len(selected) >= 10:
                break
        return "\n".join(selected) if selected else None

    def _first_match(self, lines: list[str], pattern: re.Pattern[str]) -> str | None:
        for line in lines:
            match = pattern.search(line)
            if match:
                return match.group(0).strip()
        return None

    def _label_block(self, lines: list[str], label_re: re.Pattern[str]) -> str | None:
        for index, line in enumerate(lines):
            if not label_re.search(line):
                continue
            block = [line]
            for next_line in lines[index + 1 : index + 5]:
                if self.RESPONDENT_LABEL_RE.search(next_line) and label_re is self.PETITIONER_LABEL_RE:
                    break
                if self.PETITIONER_LABEL_RE.search(next_line) and label_re is self.RESPONDENT_LABEL_RE:
                    break
                if re.search(r"\b(versus|vs\.?|v/s)\b", next_line, re.IGNORECASE) and len(block) > 1:
                    break
                block.append(next_line)
            return "\n".join(block)
        return None

    def _advocate_block(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if not self.ADVOCATE_TABLE_RE.search(line):
                continue
            block = lines[index : index + 8]
            return "\n".join(block) if block else None
        return None

    def _rejected_candidate_hints(self, lines: list[str]) -> list[dict[str, str]]:
        hints: list[dict[str, str]] = []
        rules: list[tuple[str, re.Pattern[str]]] = [
            ("form_instruction", re.compile(r"\b(to be filled by|date\s*:?)\b", re.IGNORECASE)),
            ("contains_age_phrase", re.compile(r"\baged?\s+about\b", re.IGNORECASE)),
            ("contains_court_heading", re.compile(r"\bin the high court\b", re.IGNORECASE)),
            ("contains_versus", re.compile(r"\b(versus|vs\.?|v/s)\b", re.IGNORECASE)),
            ("index_or_declaration_text", re.compile(r"\b(index|description of documents|declaration|annexure)\b", re.IGNORECASE)),
            ("body_paragraph", re.compile(r"^\s*\d+(?:\.\d+)?\s*that\b", re.IGNORECASE)),
        ]
        for line in lines:
            if len(line) > 160:
                hints.append({"value": line[:220], "reason": "too_long_for_single_field"})
                continue
            for reason, pattern in rules:
                if pattern.search(line):
                    hints.append({"value": line[:220], "reason": reason})
                    break
        return hints[:30]

    def _build_page_route_map(self, routes: dict[str, Any]) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        for field_key in self.FIELD_KEYS:
            for route in routes.get(field_key, [])[:5]:
                try:
                    page_no = int(route.get("page_no"))
                except Exception:
                    continue
                out.setdefault(page_no, {})[field_key] = {
                    "route_score": route.get("score"),
                    "reasons": route.get("reasons") or [],
                    "matched_keywords": route.get("matched_keywords") or [],
                    "negative_keywords": route.get("negative_keywords") or [],
                }
        return out

    def _route_debug(self, field_key: str, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "page_no": route.get("page_no"),
                "route_score": route.get("score"),
                "reason": route.get("reasons") or [],
                "matched_keywords": route.get("matched_keywords") or [],
                "negative_keywords": route.get("negative_keywords") or [],
                "text_preview": route.get("text_excerpt") or route.get("text_preview") or "",
            }
            for route in routes[:5]
        ]
