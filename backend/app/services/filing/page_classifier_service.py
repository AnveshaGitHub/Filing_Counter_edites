from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.schemas.page_classification import (
    DocumentClassificationResult,
    PageClassificationResult,
)

"""
Canonical page classifier for persisted document pages.

Use this service when code needs one page type per page plus confidence/reasons
for APIs, v2 extractors, layout-aware extraction, and benchmark reporting.
Lower-level retrieval scoring still uses utils.page_layout_analyzer because it
can attach multiple lightweight page tags to chunks.
"""


@dataclass
class PageInput:
    page_no: int
    text: str


class PageClassifierService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def normalize(self, text: str | None) -> str:
        if not text:
            return ""
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def classify_text(self, page_no: int, text: str | None) -> PageClassificationResult:
        clean = self.normalize(text)
        low = clean.lower()
        reasons: list[str] = []

        if len(clean) < 30:
            return PageClassificationResult(
                page_no=page_no,
                page_type="blank_or_low_text",
                confidence=0.9,
                reasons=["text_length_lt_30"],
                text_preview=clean[:220],
            )

        def has_any(words: list[str]) -> bool:
            return any(word in low for word in words)

        if has_any(["scrutiny report", "checker", "court fee", "subject heading", "provision of law"]):
            reasons.append("scrutiny_or_subject_metadata")
            return PageClassificationResult(
                page_no=page_no,
                page_type="filing_scrutiny_report",
                confidence=0.92,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if "in the high court" in low and has_any(
            ["applicant", "petitioner", "appellant", "respondent", "versus", "vs."]
        ):
            reasons.append("high_court_cause_title_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="hc_cause_title",
                confidence=0.9,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["name of first plaintiff", "first defendant", "record room"]) and has_any(["suit", "appeal"]):
            reasons.append("lower_court_title_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="lower_court_title",
                confidence=0.88,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["order sheet", "order or proceeding", "signature of presiding officer", "pleaders where necessary"]):
            reasons.append("order_sheet_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="lower_court_order_sheet",
                confidence=0.9,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["memo of appearance", "advocate for applicant", "advocate for appellant", "counsel for applicant"]):
            reasons.append("appearance_advocate_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="memo_of_appearance",
                confidence=0.85,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if "vakalatnama" in low:
            reasons.append("vakalatnama_signal")
            return PageClassificationResult(
                page_no=page_no,
                page_type="vakalatnama",
                confidence=0.85,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["index", "description of documents", "annexure", "page no"]):
            reasons.append("index_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="index_page",
                confidence=0.78,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["criminal law", "procedure", "category/sub-category", "provision of law", "act / section"]):
            reasons.append("legal_metadata_noise")
            return PageClassificationResult(
                page_no=page_no,
                page_type="legal_provision_noise",
                confidence=0.82,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["judgment", "order", "convicted", "acquitted", "sentence", "pronounced"]):
            reasons.append("judgment_order_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="judgment_order",
                confidence=0.68,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if has_any(["application under section", "bail application", "petition under", "application for"]):
            reasons.append("application_petition_signals")
            return PageClassificationResult(
                page_no=page_no,
                page_type="application_petition",
                confidence=0.68,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if "affidavit" in low:
            reasons.append("affidavit_signal")
            return PageClassificationResult(
                page_no=page_no,
                page_type="affidavit",
                confidence=0.75,
                reasons=reasons,
                text_preview=clean[:220],
            )

        if "annexure" in low or re.search(r"\bdocument[-\s]?[a-z]/\d+\b", low):
            reasons.append("annexure_signal")
            return PageClassificationResult(
                page_no=page_no,
                page_type="annexure",
                confidence=0.7,
                reasons=reasons,
                text_preview=clean[:220],
            )

        return PageClassificationResult(
            page_no=page_no,
            page_type="unknown",
            confidence=0.35,
            reasons=["no_strong_signal"],
            text_preview=clean[:220],
        )

    def classify_document(self, document_id: int, pages: list[PageInput]) -> DocumentClassificationResult:
        page_results = [self.classify_text(page.page_no, page.text) for page in pages]
        counts: dict[str, int] = {}
        for page in page_results:
            counts[page.page_type] = counts.get(page.page_type, 0) + 1

        total = max(len(page_results), 1)
        first_10_types = {page.page_type for page in page_results if page.page_no <= 10}
        reasons: list[str] = []

        has_hc = counts.get("hc_cause_title", 0) > 0
        has_lower = counts.get("lower_court_title", 0) > 0
        has_order = counts.get("lower_court_order_sheet", 0) > 0

        if counts.get("lower_court_order_sheet", 0) / total >= 0.35:
            reasons.append("order_sheet_ratio_high")
            document_type = "order_sheet_bundle"
            confidence = 0.86
        elif has_lower and has_hc:
            reasons.append("mixed_hc_and_lower_court_signals")
            document_type = "mixed"
            confidence = 0.72
        elif has_lower:
            reasons.append("lower_court_title_found")
            document_type = "lower_court_record"
            confidence = 0.84
        elif "hc_cause_title" in first_10_types:
            reasons.append("hc_cause_title_found_in_first_10")
            document_type = "hc_filing"
            confidence = 0.82
        elif has_hc and has_order:
            reasons.append("mixed_hc_and_order_sheet_signals")
            document_type = "mixed"
            confidence = 0.72
        else:
            reasons.append("unknown_or_mixed_document")
            document_type = "unknown"
            confidence = 0.45

        return DocumentClassificationResult(
            document_id=document_id,
            document_type=document_type,
            confidence=confidence,
            reasons=reasons,
            pages=page_results,
        )

    def load_pages_from_db(self, document_id: int) -> list[PageInput]:
        if self.db is None:
            return []

        try:
            from app.models.local_test_document_page import LocalTestDocumentPage

            rows = (
                self.db.query(LocalTestDocumentPage)
                .filter(LocalTestDocumentPage.document_id == document_id)
                .order_by(LocalTestDocumentPage.page_no.asc())
                .all()
            )
            if rows:
                return [PageInput(page_no=row.page_no, text=row.ocr_text or "") for row in rows]
        except Exception:
            pass

        try:
            from app.models.document_page import DocumentPage

            rows = (
                self.db.query(DocumentPage)
                .filter(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_no.asc())
                .all()
            )
            return [PageInput(page_no=row.page_no, text=row.ocr_text or "") for row in rows]
        except Exception:
            return []

    def classify_document_from_db(self, document_id: int) -> DocumentClassificationResult:
        return self.classify_document(
            document_id=document_id,
            pages=self.load_pages_from_db(document_id),
        )

    def allowed_page_types_for_field(self, field_key: str) -> set[str]:
        mapping = {
            "case_type": {"hc_cause_title", "lower_court_title", "filing_scrutiny_report", "index_page"},
            "list_type": {"filing_scrutiny_report", "hc_cause_title"},
            "petitioner_name": {"hc_cause_title", "lower_court_title", "application_petition"},
            "respondent_name": {"hc_cause_title", "lower_court_title", "application_petition"},
            "advocate_name": {"memo_of_appearance", "vakalatnama", "hc_cause_title"},
            "advocate_enrol_no": {"memo_of_appearance", "vakalatnama"},
            "phone_mobile": {"memo_of_appearance", "vakalatnama", "application_petition"},
            "address": {"hc_cause_title", "application_petition"},
        }
        return mapping.get(field_key, {"hc_cause_title", "application_petition"})

    def page_priority_score_for_field(self, field_key: str, page_type: str) -> float:
        if page_type in self.allowed_page_types_for_field(field_key):
            if page_type == "hc_cause_title":
                return 1.25
            if page_type == "lower_court_title":
                return 1.18
            if page_type in {"memo_of_appearance", "vakalatnama"}:
                return 1.15
            return 1.0

        if page_type in {"legal_provision_noise", "lower_court_order_sheet", "blank_or_low_text"}:
            return 0.2

        return 0.5
