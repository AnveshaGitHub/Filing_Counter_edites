from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from sqlalchemy.orm import Session

from app.models.extraction_job import ExtractionJob
from app.models.extracted_field import ExtractedField
from app.models.local_test_document import LocalTestDocument
from app.models.local_test_document_page import LocalTestDocumentPage
from app.schemas.filing_full_metadata import FilingFullMetadata
from app.services.filing.candidate_persistence_service import CandidatePersistenceService
from app.services.filing.filing_candidate_pipeline_service import FilingCandidatePipelineService
from app.services.filing.filing_full_metadata_service import FilingFullMetadataService


MAIN_FIELD_LABELS = {
    "case_type": "Case Type",
    "list_type": "List Type",
    "with_application": "With Application",
    "petitioner_party_type": "Petitioner Type",
    "petitioner_name": "Petitioner Name",
    "petitioner_relation": "Petitioner Relation",
    "petitioner_father_husband_name": "Petitioner Father/Husband",
    "petitioner_age": "Petitioner Age",
    "petitioner_occupation": "Petitioner Occupation",
    "petitioner_address": "Petitioner Address",
    "petitioner_state": "Petitioner State",
    "petitioner_district": "Petitioner District",
    "petitioner_tehsil": "Petitioner Tehsil",
    "petitioner_phone_mobile": "Petitioner Phone/Mobile",
    "petitioner_email_id": "Petitioner Email",
    "petitioner_pincode": "Petitioner Pincode",
    "petitioner_caste": "Petitioner Caste",
    "respondent_party_type": "Respondent Type",
    "respondent_name": "Respondent Name",
    "respondent_relation": "Respondent Relation",
    "respondent_father_husband_name": "Respondent Father/Husband",
    "respondent_age": "Respondent Age",
    "respondent_occupation": "Respondent Occupation",
    "respondent_address": "Respondent Address",
    "respondent_state": "Respondent State",
    "respondent_district": "Respondent District",
    "respondent_tehsil": "Respondent Tehsil",
    "respondent_phone_mobile": "Respondent Phone/Mobile",
    "respondent_email_id": "Respondent Email",
    "respondent_pincode": "Respondent Pincode",
    "respondent_caste": "Respondent Caste",
    "advocate_name": "Main Advocate Name",
    "advocate_enrol_no": "Main Advocate Enrol No",
    "advocate_enrol_year": "Main Advocate Enrol Year",
    "advocate_mobile": "Main Advocate Mobile",
    "advocate_remark": "Advocate Remark",
    "hide_party_petitioner": "Hide Party Petitioner",
    "hide_party_respondent": "Hide Party Respondent",
    "differently_abled_petitioner": "Differently Abled Petitioner",
    "differently_abled_respondent": "Differently Abled Respondent",
}

LOWER_COURT_FIELDS = [
    "lower_court_type",
    "lower_court_cnr_no",
    "lower_court_district",
    "lower_court_tehsil",
    "lower_court_case_type",
    "lower_court_case_no",
    "lower_court_new_case_no",
    "lower_court_case_year",
    "impugned_judgment_date",
    "judge_designation",
    "judge_name",
    "police_station",
    "crime_no",
    "crime_year",
    "impugned_brief_description",
    "impugned_subject_law",
]

METADATA_FIELDS = [
    "case_no",
    "case_year",
    "filing_no",
    "filing_year",
    "case_title",
    "category_text",
    "category_code",
    "sub_category_text",
    "sub_category_code",
    "provision_of_law",
    "act",
    "section",
    "claim_amount",
    "relief_claimed",
    "petitioner_main_advocate",
    "petitioner_main_advocate_no",
    "petitioner_main_advocate_year",
    "petitioner_main_advocate_mobile",
    "respondent_main_advocate",
    "respondent_main_advocate_no",
    "respondent_main_advocate_year",
    "respondent_main_advocate_mobile",
]


@dataclass
class CheckRow:
    section: str
    field_key: str
    label: str
    filled: bool
    value: str
    confidence: float | None
    source: str
    reason: str
    evidence: str
    recommendation: str


class ExtractionCheckpointReportService:
    """Creates a post-run diagnostic report without changing extraction behavior."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.candidates = CandidatePersistenceService(db)
        self.metadata_service = FilingFullMetadataService(db)

    def build_pdf(self, document_id: int, refresh_candidates: bool = True) -> tuple[bytes, str]:
        payload = self.build_payload(document_id=document_id, refresh_candidates=refresh_candidates)
        content = self._render_pdf(payload)
        base = payload["document"]["filename_base"]
        return content, f"{document_id}_{base}_checkpoint_report.pdf"

    def build_payload(self, document_id: int, refresh_candidates: bool = True) -> dict[str, Any]:
        doc = self.db.query(LocalTestDocument).filter(LocalTestDocument.id == document_id).first()
        if not doc:
            raise ValueError("local_test_document_not_found")

        if refresh_candidates:
            try:
                candidate_debug = FilingCandidatePipelineService(self.db).build_candidates(document_id)
            except Exception as exc:
                candidate_debug = {"error": str(exc)}
        else:
            candidate_debug = {"refresh_skipped": True}

        job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.document_id == document_id)
            .order_by(ExtractionJob.id.desc())
            .first()
        )
        field_rows = []
        if job:
            field_rows = (
                self.db.query(ExtractedField)
                .filter(ExtractedField.extraction_job_id == job.id)
                .order_by(ExtractedField.id.asc())
                .all()
            )

        pages = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        page_stats = self._page_stats(pages)
        candidate_rows = self.candidates.list_candidates(document_id)
        metadata = self.metadata_service.get(document_id)

        rows = self._build_rows(
            fields=field_rows,
            metadata=metadata,
            candidates=candidate_rows,
            page_stats=page_stats,
        )
        summary = {
            "total_fields_checked": len(rows),
            "filled": sum(1 for row in rows if row.filled),
            "missing": sum(1 for row in rows if not row.filled),
            "missing_by_reason": self._missing_by_reason(rows),
        }
        return {
            "document": {
                "document_id": document_id,
                "filename": doc.original_filename,
                "filename_base": Path(doc.original_filename or f"document_{document_id}").stem,
                "status": doc.status,
                "stored_path": doc.stored_path,
                "notes": doc.notes,
            },
            "job": {
                "extraction_job_id": job.id if job else None,
                "status": job.status if job else "missing",
                "extractor_version": job.extractor_version if job else None,
                "overall_confidence": job.overall_confidence if job else None,
                "needs_review": job.needs_review if job else None,
            },
            "page_stats": page_stats,
            "candidate_debug": candidate_debug,
            "rows": [row.__dict__ for row in rows],
            "summary": summary,
        }

    def _build_rows(
        self,
        fields: list[ExtractedField],
        metadata: FilingFullMetadata,
        candidates: list[dict[str, Any]],
        page_stats: dict[str, Any],
    ) -> list[CheckRow]:
        extracted = {row.field_key: row for row in fields}
        candidates_by_key: dict[str, list[dict[str, Any]]] = {}
        for candidate in candidates:
            candidates_by_key.setdefault(str(candidate.get("field_key") or ""), []).append(candidate)

        rows: list[CheckRow] = []
        for field_key, label in MAIN_FIELD_LABELS.items():
            row = extracted.get(field_key)
            rows.append(self._field_row("Main Extraction", field_key, label, row, candidates_by_key, page_stats))

        for field_key in METADATA_FIELDS:
            rows.append(self._metadata_row("Case Metadata", field_key, metadata, candidates_by_key, page_stats))

        for field_key in LOWER_COURT_FIELDS:
            rows.append(self._metadata_row("Lower Court", field_key, metadata, candidates_by_key, page_stats))

        rows.extend(self._collection_rows("Additional Parties", metadata.extra_parties, "extra_parties", page_stats))
        rows.extend(
            self._collection_rows(
                "Additional Petitioner Advocates",
                metadata.petitioner_extra_advocates,
                "petitioner_extra_advocates",
                page_stats,
            )
        )
        rows.extend(
            self._collection_rows(
                "Additional Respondent Advocates",
                metadata.respondent_extra_advocates,
                "respondent_extra_advocates",
                page_stats,
            )
        )
        return rows

    def _field_row(
        self,
        section: str,
        field_key: str,
        label: str,
        row: ExtractedField | None,
        candidates_by_key: dict[str, list[dict[str, Any]]],
        page_stats: dict[str, Any],
    ) -> CheckRow:
        value = self._clean(row.normalized_value if row else None) or self._clean(row.raw_value if row else None)
        filled = bool(value)
        candidates = candidates_by_key.get(field_key, [])
        reason, recommendation = self._reason(filled, row.status if row else None, row.validation_notes if row else None, candidates, page_stats)
        return CheckRow(
            section=section,
            field_key=field_key,
            label=label,
            filled=filled,
            value=value,
            confidence=float(row.confidence) if row and row.confidence is not None else None,
            source=row.source_type if row else "",
            reason="filled" if filled else reason,
            evidence=self._clean(row.evidence_text if row else "")[:240],
            recommendation="No action needed." if filled else recommendation,
        )

    def _metadata_row(
        self,
        section: str,
        field_key: str,
        metadata: FilingFullMetadata,
        candidates_by_key: dict[str, list[dict[str, Any]]],
        page_stats: dict[str, Any],
    ) -> CheckRow:
        value = self._clean(getattr(metadata, field_key, None))
        candidates = candidates_by_key.get(field_key, [])
        reason, recommendation = self._reason(bool(value), None, None, candidates, page_stats)
        return CheckRow(
            section=section,
            field_key=field_key,
            label=field_key.replace("_", " ").title(),
            filled=bool(value),
            value=value,
            confidence=None,
            source="full_metadata" if value else "",
            reason="filled" if value else reason,
            evidence="",
            recommendation="No action needed." if value else recommendation,
        )

    def _collection_rows(
        self,
        section: str,
        items: list[Any],
        field_key: str,
        page_stats: dict[str, Any],
    ) -> list[CheckRow]:
        filled = bool(items)
        values = []
        for item in items or []:
            data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            name = data.get("name") or data.get("advocate_name") or data.get("party_no") or ""
            if name:
                values.append(str(name))
        reason = "filled" if filled else ("text_not_extracted" if page_stats["empty_pages"] == page_stats["total_pages"] else "no_structured_rows_mapped")
        recommendation = "No action needed." if filled else "Check graph parser, table parser, and autofill mapping for this section."
        return [
            CheckRow(
                section=section,
                field_key=field_key,
                label=section,
                filled=filled,
                value=", ".join(values[:8]),
                confidence=None,
                source="full_metadata",
                reason=reason,
                evidence="",
                recommendation=recommendation,
            )
        ]

    def _reason(
        self,
        filled: bool,
        status: str | None,
        validation_note: str | None,
        candidates: list[dict[str, Any]],
        page_stats: dict[str, Any],
    ) -> tuple[str, str]:
        if filled:
            return "filled", "No action needed."
        if page_stats["empty_pages"] == page_stats["total_pages"]:
            return "text_not_extracted", "OCR produced no usable text. Reprocess OCR or use vision OCR text fallback."
        if page_stats["low_confidence_pages"] >= max(1, page_stats["total_pages"] // 2):
            if not candidates:
                return "ocr_low_confidence_no_candidate", "OCR is weak and parser found no candidate. Run vision fallback on important pages."
        if not candidates:
            return "no_candidate_found", "Text exists, but no extractor matched this field. Add parser keywords/patterns or graph mapping."
        rejected = [row for row in candidates if row.get("status") == "rejected"]
        if len(rejected) == len(candidates):
            notes = ", ".join(sorted({str(row.get("validation_note") or "rejected") for row in rejected}))[:160]
            return "validation_rejected", f"Candidates were rejected by validation: {notes}."
        best = max(candidates, key=lambda row: float(row.get("confidence") or 0.0))
        best_conf = float(best.get("confidence") or 0.0)
        if best_conf < 0.74:
            return "candidate_low_confidence", "Candidate exists but confidence is below autofill threshold. Improve OCR/page routing or parser scoring."
        values = {
            str(row.get("normalized_value") or row.get("value") or "").strip().upper()
            for row in candidates
            if row.get("value")
        }
        if len(values) > 1:
            return "candidate_conflict", "Multiple different candidates found. Add merge/rerank rule or source priority."
        if status == "missing":
            return "not_mapped_to_form", "A candidate may exist, but it was not promoted into the form field. Check autofill mapper."
        if validation_note:
            return "validation_or_quality_gate", f"Validation note: {validation_note}"
        return "unknown_blocker", "Candidate exists but field remained empty. Inspect evidence and mapper logs."

    def _page_stats(self, pages: list[LocalTestDocumentPage]) -> dict[str, Any]:
        total = len(pages)
        empty = 0
        low_conf = 0
        methods: dict[str, int] = {}
        sample_empty_pages: list[int] = []
        sample_low_conf_pages: list[int] = []
        for page in pages:
            text = self._clean(page.ocr_text)
            if not text:
                empty += 1
                if len(sample_empty_pages) < 10:
                    sample_empty_pages.append(page.page_no)
            conf = page.ocr_confidence if page.ocr_confidence is not None else page.ocr_avg_confidence
            if conf is not None and conf < 0.70:
                low_conf += 1
                if len(sample_low_conf_pages) < 10:
                    sample_low_conf_pages.append(page.page_no)
            method = page.extraction_method or "unknown"
            methods[method] = methods.get(method, 0) + 1
        return {
            "total_pages": total,
            "empty_pages": empty,
            "low_confidence_pages": low_conf,
            "sample_empty_pages": sample_empty_pages,
            "sample_low_confidence_pages": sample_low_conf_pages,
            "extraction_methods": methods,
        }

    def _missing_by_reason(self, rows: list[CheckRow]) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            if row.filled:
                continue
            out[row.reason] = out.get(row.reason, 0) + 1
        return out

    def _render_pdf(self, payload: dict[str, Any]) -> bytes:
        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        margin = 42
        y = margin
        line_height = 12
        max_y = 800

        def add_line(text: str = "", size: int = 9, color: tuple[float, float, float] = (0, 0, 0)) -> None:
            nonlocal page, y
            if y > max_y:
                page = pdf.new_page(width=595, height=842)
                y = margin
            page.insert_text((margin, y), self._pdf_safe(text), fontsize=size, fontname="helv", color=color)
            y += line_height + (2 if size >= 12 else 0)

        def add_wrapped(text: str, size: int = 9, indent: int = 0) -> None:
            width = 98 - indent
            for line in textwrap.wrap(self._pdf_safe(text), width=width) or [""]:
                nonlocal page, y
                if y > max_y:
                    page = pdf.new_page(width=595, height=842)
                    y = margin
                page.insert_text((margin + indent * 4, y), line, fontsize=size, fontname="helv")
                y += line_height

        document = payload["document"]
        job = payload["job"]
        summary = payload["summary"]
        add_line("Extraction Checkpoint Report", size=16)
        add_line(f"Document: {document['document_id']} | {document['filename']}", size=10)
        add_line(f"Job: {job['extraction_job_id']} | status={job['status']} | confidence={job['overall_confidence']}", size=9)
        add_line("")
        add_line("Summary", size=13)
        add_line(f"Fields checked: {summary['total_fields_checked']} | filled: {summary['filled']} | missing: {summary['missing']}")
        add_wrapped(f"Missing by reason: {json.dumps(summary['missing_by_reason'], ensure_ascii=False)}")
        add_wrapped(f"Page stats: {json.dumps(payload['page_stats'], ensure_ascii=False)}")
        add_wrapped(f"Candidate pipeline: {json.dumps(payload['candidate_debug'], ensure_ascii=False)[:900]}")
        add_line("")

        last_section = ""
        for row in payload["rows"]:
            if row["section"] != last_section:
                add_line("")
                add_line(row["section"], size=13)
                last_section = row["section"]
            marker = "OK" if row["filled"] else "MISSING"
            add_wrapped(
                f"[{marker}] {row['label']} ({row['field_key']}) | value={row['value'] or '-'} | "
                f"confidence={row['confidence'] if row['confidence'] is not None else '-'} | "
                f"source={row['source'] or '-'} | reason={row['reason']}",
                size=9,
            )
            if not row["filled"]:
                add_wrapped(f"Recommendation: {row['recommendation']}", size=8, indent=2)
            if row.get("evidence"):
                add_wrapped(f"Evidence: {row['evidence']}", size=8, indent=2)

        content = pdf.tobytes()
        pdf.close()
        return content

    def _clean(self, value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    def _pdf_safe(self, text: str) -> str:
        return "".join(char for char in str(text) if char == "\t" or ord(char) >= 32)
