from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.extraction_job import ExtractionJob
from app.models.extracted_field import ExtractedField
from app.models.local_test_document_page import LocalTestDocumentPage
from app.schemas.document_type import DocumentTypeDecision, LowerCourtCandidate
from app.schemas.filing_extraction import (
    ExtractionResponse,
    ExtractionRunRequest,
    ExtractionJobSummary,
    FieldEvidence,
    FieldResult,
    FieldCandidate,
)
from app.services.filing.field_registry_service import FieldRegistryService
from app.services.filing.filing_retrieval_service import FilingRetrievalService
from app.services.filing.candidate_extraction_service import CandidateExtractionService
from app.services.filing.field_validation_service import FieldValidationService
from app.services.filing.confidence_scoring_service import ConfidenceScoringService
from app.services.filing.feedback_rerank_service import FeedbackRerankService
from app.services.filing.document_type_router_service import DocumentTypeRouterService
from app.services.filing.lower_court_extractor import LowerCourtExtractor
from app.services.filing.page_priority_service import PagePriorityService, PageText
from app.services.filing.v2_extractors import FieldSpecificExtractionService
from app.services.filing.utils.field_grouping import build_grouped_fields
from app.services.filing.utils.advocate_row_builder import build_advocate_rows
from app.services.filing.utils.party_details_builder import build_party_more_details
from app.services.filing.utils.multi_party_builder import build_party_suggestions
from app.services.filing.utils.review_flags import (
    add_conflict_flag,
    add_low_confidence_flag,
    add_missing_required_flag,
)
from app.services.filing.utils.page_layout_analyzer import page_priority_multiplier
from app.services.filing.utils.suggestion_formatter import (
    clean_advocate_candidate,
    clean_party_name_candidate,
    clean_respondent_candidate,
    should_reject_advocate_candidate,
    should_reject_name_candidate,
    should_reject_party_candidate,
)

logger = logging.getLogger(__name__)


class FilingExtractionService:
    V2_MERGE_FLAG = "v2_merge_applied"
    V2_MERGE_VERSION = "v2_merge"

    SUGGESTION_LIMITS = {
        "case_type": 3,
        "list_type": 3,
        "petitioner_name": 3,
        "respondent_name": 3,
        "petitioner_party_type": 3,
        "respondent_party_type": 3,
        "advocate_name": 2,
        "advocate_enrol_no": 2,
        "advocate_mobile": 2,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = FieldRegistryService()
        self.retrieval = FilingRetrievalService(db)
        self.candidate_extractor = CandidateExtractionService()
        self.validator = FieldValidationService()
        self.scorer = ConfidenceScoringService()
        self.feedback_reranker = FeedbackRerankService(db)
        self.document_type_router = DocumentTypeRouterService()
        self.page_priority_service = PagePriorityService()

    def create_job(self, document_id: int, payload: ExtractionRunRequest) -> ExtractionJob:
        job = ExtractionJob(
            document_id=document_id,
            form_type=payload.form_type,
            status="queued" if payload.run_async else "running",
            extractor_version="v5_phase_5",
            triggered_by=payload.triggered_by,
            started_at=None if payload.run_async else datetime.utcnow(),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _delete_existing_job_fields(self, extraction_job_id: int) -> None:
        (
            self.db.query(ExtractedField)
            .filter(ExtractedField.extraction_job_id == extraction_job_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()

    def _has_conflict(self, candidates: list[dict]) -> bool:
        normalized_values = {
            str(c.get("normalized_value") or c.get("value") or "").strip()
            for c in candidates
            if c.get("value") and not isinstance(c.get("value"), dict)
        }
        normalized_values.discard("")
        return len(normalized_values) > 1

    def _clean_suggestion_by_field(self, field_key: str, value: str) -> tuple[str, bool]:
        cleaned = value.strip()
        if cleaned.lower().startswith("about:blank"):
            cleaned = cleaned[len("about:blank"):].strip()
        if not cleaned:
            return "", True
        if field_key == "petitioner_name":
            cleaned = clean_party_name_candidate(cleaned)
            return cleaned, should_reject_name_candidate(cleaned)
        if field_key == "respondent_name":
            cleaned = clean_respondent_candidate(cleaned)
            return cleaned, should_reject_party_candidate(cleaned)
        if field_key == "advocate_name":
            cleaned = clean_advocate_candidate(cleaned)
            return cleaned, should_reject_advocate_candidate(cleaned)
        return cleaned, False

    def _to_candidate_schema(self, items: list[dict], field_def) -> list[FieldCandidate]:
        result: list[FieldCandidate] = []
        limit = self.SUGGESTION_LIMITS.get(field_def.key, 3)
        seen: set[str] = set()
        for item in items:
            raw_value = item.get("value")
            if isinstance(raw_value, dict) or not raw_value:
                continue
            cleaned, rejected = self._clean_suggestion_by_field(field_def.key, str(raw_value))
            if rejected or not cleaned:
                continue
            normalized = self.validator.normalize_value(field_def, cleaned)
            norm_key = str(normalized or cleaned).strip()
            if not norm_key or norm_key in seen:
                continue
            seen.add(norm_key)
            result.append(
                FieldCandidate(
                    value=cleaned,
                    normalized_value=normalized,
                    confidence=float(item.get("confidence", 0.0)),
                    status="suggested",
                    evidence=FieldEvidence(
                        source_type=item.get("source_type"),
                        page_from=item.get("page_from"),
                        page_to=item.get("page_to"),
                        chunk_id=item.get("chunk_id"),
                        text=item.get("evidence_text"),
                        validation_notes=None,
                    ),
                )
            )
            if len(result) >= limit:
                break
        return result

    def _log_top_candidates(self, field_key: str, candidates: list[dict], n: int = 5) -> None:
        if field_key not in {"case_type", "petitioner_name", "respondent_name", "advocate_name"}:
            return
        preview = []
        for item in candidates[:n]:
            preview.append(
                {
                    "value": item.get("value"),
                    "confidence": round(float(item.get("confidence", 0.0)), 3),
                    "source": item.get("source_type"),
                    "page": item.get("page_from"),
                    "page_types": item.get("page_types"),
                }
            )
        logger.info("[EXTRACTION][%s] top_candidates=%s", field_key, preview)

    def _load_page_texts(self, document_id: int) -> list[PageText]:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        pages: list[PageText] = []
        for row in rows:
            pages.append(
                PageText(
                    page_no=row.page_no,
                    text=row.ocr_text or "",
                    page_type=getattr(row, "page_type", None) or getattr(row, "detected_page_type", None),
                )
            )
        return pages

    def _field_bucket(self, response: ExtractionResponse, field_key: str) -> FieldResult | None:
        for field in response.fields:
            if field.field_key == field_key:
                return field
        return None

    def _page_type_for_page(self, pages: list[PageText], page_no: int | None) -> str | None:
        if page_no is None:
            return None
        for page in pages:
            if page.page_no == page_no:
                page_type, _, _ = self.page_priority_service.score_page(page)
                return page_type
        return None

    def _append_lower_court_suggestion(
        self,
        response: ExtractionResponse,
        candidate: LowerCourtCandidate,
    ) -> None:
        field = self._field_bucket(response, candidate.field_key)
        if not field:
            return

        normalized = self.validator.normalize_value(self.registry.get(candidate.field_key), candidate.value)
        suggestion = FieldCandidate(
            value=candidate.value,
            normalized_value=normalized,
            confidence=candidate.confidence,
            status="suggested",
            evidence=FieldEvidence(
                source_type=candidate.source,
                page_from=candidate.page_no,
                page_to=candidate.page_no,
                chunk_id=None,
                text=candidate.evidence,
                validation_notes="lower_court_hint_review_required"
                if candidate.confidence < 0.85
                else None,
            ),
        )

        existing_keys = {
            (item.normalized_value or item.value or "").strip().upper()
            for item in field.suggestions
        }
        suggestion_key = (suggestion.normalized_value or suggestion.value or "").strip().upper()
        if suggestion_key and suggestion_key not in existing_keys:
            field.suggestions.insert(0, suggestion)
            field.suggestions = field.suggestions[: self.SUGGESTION_LIMITS.get(field.field_key, 3)]

    def _merge_lower_court_candidates(
        self,
        response: ExtractionResponse,
        candidates: list[LowerCourtCandidate],
        decision: DocumentTypeDecision,
        pages: list[PageText],
    ) -> ExtractionResponse:
        if not candidates:
            return response

        review_flags = set(response.review_flags)
        review_flags.add(f"document_type:{decision.document_type}")

        for field_key in {"petitioner_name", "respondent_name"}:
            field = self._field_bucket(response, field_key)
            if not field or not field.evidence:
                continue
            page_type = self._page_type_for_page(pages, field.evidence.page_from)
            if page_type in {"order_sheet_page", "order_copy_page"}:
                if field.value:
                    field.suggestions.insert(
                        0,
                        FieldCandidate(
                            value=field.value,
                            normalized_value=field.normalized_value,
                            confidence=min(field.confidence, 0.35),
                            status="suggested",
                            evidence=FieldEvidence(
                                source_type=field.evidence.source_type,
                                page_from=field.evidence.page_from,
                                page_to=field.evidence.page_to,
                                chunk_id=field.evidence.chunk_id,
                                text=field.evidence.text,
                                validation_notes="downgraded_order_sheet_evidence",
                            ),
                        ),
                    )
                field.value = None
                field.normalized_value = None
                field.status = "missing"
                field.confidence = min(field.confidence, 0.25)
                if field.evidence:
                    field.evidence.validation_notes = "order_sheet_page_not_trusted_for_party_name"
                review_flags.add(f"{field_key}:order_sheet_page_not_trusted")

        for candidate in candidates:
            if candidate.field_key in {"case_type", "petitioner_name", "respondent_name"}:
                self._append_lower_court_suggestion(response, candidate)
            else:
                review_flags.add(
                    f"{candidate.field_key}:{candidate.value}:page_{candidate.page_no}"
                )

        for field in response.fields:
            if field.field_key in {"case_type", "petitioner_name", "respondent_name"} and field.suggestions:
                if field.status == "missing":
                    field.status = "suggested"
                if not field.value:
                    field.confidence = max(field.confidence, min(field.suggestions[0].confidence, 0.84))

        response.review_flags = sorted(review_flags)
        response.confirmed_count = sum(1 for field in response.fields if field.status == "confirmed")
        response.suggested_count = sum(1 for field in response.fields if field.status == "suggested")
        response.missing_count = sum(1 for field in response.fields if field.status == "missing")
        response.job.needs_review = True
        response.job.status = "needs_review"

        return response

    def _merge_v2_candidates(self, response, v2_candidates):
        if not v2_candidates:
            return response

        from app.services.filing.field_quality_gate_service import FieldQualityGateService

        quality_gate = FieldQualityGateService()

        by_field: dict[str, list] = {}
        for cand in v2_candidates:
            if getattr(cand, "status", None) == "rejected":
                continue
            by_field.setdefault(cand.field_key, []).append(cand)

        for key in by_field:
            by_field[key].sort(key=lambda c: c.confidence, reverse=True)

        def aliases_for_field(field_key: str, section_name: str | None = None) -> list[str]:
            aliases = [field_key]

            generic_fields = {
                "relation",
                "father_or_husband",
                "age",
                "occupation",
                "address",
                "district",
                "tehsil",
                "village",
                "state",
                "phone_mobile",
                "email_id",
                "pincode",
            }

            if field_key in generic_fields:
                if section_name == "petitioner_fields":
                    aliases.append(f"petitioner_{field_key}")
                elif section_name == "respondent_fields":
                    aliases.append(f"respondent_{field_key}")
                else:
                    aliases.append(f"petitioner_{field_key}")
                    aliases.append(f"respondent_{field_key}")

            return aliases

        def clean_or_replace_field(field, section_name: str | None = None):
            field_key = getattr(field, "field_key", None)
            if not field_key:
                return

            current_value = getattr(field, "value", None)
            candidates = []
            for alias in aliases_for_field(field_key, section_name):
                candidates.extend(by_field.get(alias, []))
            candidates.sort(key=lambda c: c.confidence, reverse=True)
            best = candidates[0] if candidates else None

            # First clean current value if possible.
            if current_value:
                quality = quality_gate.validate(field_key, current_value)
                if quality.status in {"accepted", "cleaned"} and quality.cleaned_value:
                    if quality.cleaned_value != current_value:
                        field.value = quality.cleaned_value
                        field.normalized_value = quality.cleaned_value
                        if hasattr(field, "evidence") and field.evidence:
                            field.evidence.validation_notes = "cleaned_by_v2_quality_gate"
                    current_is_bad = False
                else:
                    current_is_bad = True
            else:
                current_is_bad = True

            # Replace if missing/bad and v2 has clean candidate.
            if best and (not current_value or current_is_bad):
                if best.confidence >= 0.74:
                    field.value = best.value
                    field.normalized_value = best.normalized_value or best.value
                    field.confidence = best.confidence
                    field.status = "confirmed" if best.confidence >= 0.85 else "suggested"

                    if hasattr(field, "evidence") and field.evidence:
                        field.evidence.source_type = best.extractor
                        field.evidence.page_from = best.page_no
                        field.evidence.page_to = best.page_no
                        field.evidence.text = best.evidence
                        field.evidence.validation_notes = "replaced_by_v2_candidate"

            # Append v2 suggestions.
            if hasattr(field, "suggestions") and field.suggestions is not None:
                existing_values = {
                    str(getattr(s, "normalized_value", None) or getattr(s, "value", "")).strip().upper()
                    for s in field.suggestions
                }

                for c in candidates[:3]:
                    norm = str(c.normalized_value or c.value).strip().upper()
                    if norm in existing_values:
                        continue

                    try:
                        from app.schemas.filing_extraction import FieldCandidate, FieldEvidence

                        field.suggestions.append(
                            FieldCandidate(
                                value=c.value,
                                normalized_value=c.normalized_value or c.value,
                                confidence=c.confidence,
                                status="suggested",
                                evidence=FieldEvidence(
                                    source_type=c.extractor,
                                    page_from=c.page_no,
                                    page_to=c.page_no,
                                    chunk_id=None,
                                    text=c.evidence,
                                    validation_notes="v2_candidate",
                                ),
                            )
                        )
                        existing_values.add(norm)
                    except Exception:
                        pass

        # Flat response fields
        try:
            for field in response.fields:
                clean_or_replace_field(field)
        except Exception:
            logger.exception("[V2 MERGE] flat fields merge failed")

        # Grouped response fields
        try:
            grouped = response.grouped
            for section_name in ["core_fields", "petitioner_fields", "respondent_fields", "checkbox_fields"]:
                section = getattr(grouped, section_name, None)
                if not section:
                    continue
                for _, field in section.items():
                    clean_or_replace_field(field, section_name=section_name)
        except Exception:
            logger.exception("[V2 MERGE] grouped merge failed")

        self._mark_v2_merge_applied(response)

        response.confirmed_count = sum(1 for f in response.fields if f.status == "confirmed")
        response.suggested_count = sum(1 for f in response.fields if f.status == "suggested")
        response.missing_count = sum(1 for f in response.fields if f.status == "missing")

        return response

    def _mark_v2_merge_applied(self, response: ExtractionResponse) -> None:
        response.review_flags = sorted(set((response.review_flags or []) + [self.V2_MERGE_FLAG]))
        current_version = response.job.extractor_version or ""
        version_parts = [part for part in current_version.split("+") if part]
        if self.V2_MERGE_VERSION not in version_parts:
            response.job.extractor_version = "+".join([*version_parts, self.V2_MERGE_VERSION])

    def _extract_one_field(
        self,
        document_id: int,
        field_key: str,
        linked_name_value: str | None = None,
        linked_name_evidence: dict | None = None,
    ) -> tuple[FieldResult, list[dict], str | None]:
        field_def = self.registry.get(field_key)
        context = self.retrieval.build_field_context(
            document_id=document_id,
            field_key=field_key,
            linked_name_value=linked_name_value,
            linked_name_evidence=linked_name_evidence,
        )
        candidates = self.candidate_extractor.extract_candidates(field_key, context)
        candidates = self.feedback_reranker.adjust_candidate_scores(field_key, candidates)
        self._log_top_candidates(field_key, candidates)

        best = candidates[0] if candidates else None
        best_raw_value = best.get("value") if best else None
        if isinstance(best_raw_value, dict):
            best_raw_value = None

        best_source_type = best.get("source_type") if best else "system"
        best_page_from = best.get("page_from") if best else None
        best_page_to = best.get("page_to") if best else None
        best_chunk_id = best.get("chunk_id") if best else None
        best_evidence_text = best.get("evidence_text") if best else None
        best_confidence = float(best.get("confidence", 0.0)) if best else 0.0
        best_page_types = best.get("page_types") if best else []

        normalized = self.validator.normalize_value(field_def, best_raw_value)
        is_valid, validation_note = self.validator.validate(field_def, normalized)
        has_conflict = self._has_conflict(candidates)

        adjusted_conf = self.scorer.adjust_confidence(
            base_confidence=best_confidence,
            source_type=best_source_type,
            candidate_count=len(candidates),
            has_conflict=has_conflict,
            validation_note=validation_note,
            page_type_multiplier=page_priority_multiplier(best_page_types, field_key),
        )
        status = self.scorer.classify(field_def, adjusted_conf, is_valid)

        suggestions = []
        if status != "confirmed":
            suggestions = self._to_candidate_schema(candidates, field_def)

        result = FieldResult(
            field_key=field_key,
            field_label=field_def.label,
            status=status,
            value=best_raw_value,
            normalized_value=normalized,
            confidence=adjusted_conf,
            evidence=FieldEvidence(
                source_type=best_source_type,
                page_from=best_page_from,
                page_to=best_page_to,
                chunk_id=best_chunk_id,
                text=best_evidence_text,
                validation_notes=validation_note,
            ),
            suggestions=suggestions,
        )
        return result, candidates, validation_note

    def _persist_field_result(self, job_id: int, document_id: int, result: FieldResult) -> None:
        row = ExtractedField(
            extraction_job_id=job_id,
            document_id=document_id,
            field_key=result.field_key,
            field_label=result.field_label,
            raw_value=result.value,
            normalized_value=result.normalized_value,
            confidence=result.confidence,
            status=result.status,
            source_type=result.evidence.source_type if result.evidence else None,
            source_page_from=result.evidence.page_from if result.evidence else None,
            source_page_to=result.evidence.page_to if result.evidence else None,
            source_chunk_id=result.evidence.chunk_id if result.evidence else None,
            evidence_text=result.evidence.text if result.evidence else None,
            validation_notes=result.evidence.validation_notes if result.evidence else None,
        )
        self.db.add(row)

    def _run_job(self, job: ExtractionJob) -> ExtractionResponse:
        document_id = job.document_id
        self._delete_existing_job_fields(job.id)

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.error_message = None
        self.db.commit()

        field_results: list[FieldResult] = []
        review_flags: list[str] = []
        extracted_map: dict[str, FieldResult] = {}

        extraction_order = [
            "case_type",
            "list_type",
            "petitioner_name",
            "respondent_name",
        ]

        for field_key in extraction_order:
            result, candidates, _ = self._extract_one_field(document_id=document_id, field_key=field_key)
            add_conflict_flag(review_flags, field_key, candidates)
            add_low_confidence_flag(review_flags, field_key, result.confidence, threshold=0.70)
            if field_key in {"case_type", "petitioner_name", "respondent_name"}:
                add_missing_required_flag(review_flags, field_key, result.status == "missing")

            self._persist_field_result(job.id, document_id, result)
            field_results.append(result)
            extracted_map[field_key] = result

        linked_fields = [
            (
                "petitioner_party_type",
                extracted_map.get("petitioner_name").value if extracted_map.get("petitioner_name") else None,
                {
                    "page_from": extracted_map.get("petitioner_name").evidence.page_from
                    if extracted_map.get("petitioner_name")
                    and extracted_map.get("petitioner_name").evidence
                    else None,
                    "page_to": extracted_map.get("petitioner_name").evidence.page_to
                    if extracted_map.get("petitioner_name")
                    and extracted_map.get("petitioner_name").evidence
                    else None,
                    "chunk_id": extracted_map.get("petitioner_name").evidence.chunk_id
                    if extracted_map.get("petitioner_name")
                    and extracted_map.get("petitioner_name").evidence
                    else None,
                },
            ),
            (
                "respondent_party_type",
                extracted_map.get("respondent_name").value if extracted_map.get("respondent_name") else None,
                {
                    "page_from": extracted_map.get("respondent_name").evidence.page_from
                    if extracted_map.get("respondent_name")
                    and extracted_map.get("respondent_name").evidence
                    else None,
                    "page_to": extracted_map.get("respondent_name").evidence.page_to
                    if extracted_map.get("respondent_name")
                    and extracted_map.get("respondent_name").evidence
                    else None,
                    "chunk_id": extracted_map.get("respondent_name").evidence.chunk_id
                    if extracted_map.get("respondent_name")
                    and extracted_map.get("respondent_name").evidence
                    else None,
                },
            ),
        ]

        for field_key, linked_name_value, linked_name_evidence in linked_fields:
            result, candidates, _ = self._extract_one_field(
                document_id=document_id,
                field_key=field_key,
                linked_name_value=linked_name_value,
                linked_name_evidence=linked_name_evidence,
            )
            add_conflict_flag(review_flags, field_key, candidates)
            self._persist_field_result(job.id, document_id, result)
            field_results.append(result)
            extracted_map[field_key] = result

        petitioner_party_candidates_ctx = self.retrieval.build_field_context(
            document_id=document_id,
            field_key="petitioner_party_candidates",
        )
        petitioner_party_candidates = self.candidate_extractor.extract_candidates(
            "petitioner_party_candidates",
            petitioner_party_candidates_ctx,
        )
        petitioner_party_candidates = self.feedback_reranker.adjust_candidate_scores(
            "petitioner_party_candidates",
            petitioner_party_candidates,
        )

        respondent_party_candidates_ctx = self.retrieval.build_field_context(
            document_id=document_id,
            field_key="respondent_party_candidates",
        )
        respondent_party_candidates = self.candidate_extractor.extract_candidates(
            "respondent_party_candidates",
            respondent_party_candidates_ctx,
        )
        respondent_party_candidates = self.feedback_reranker.adjust_candidate_scores(
            "respondent_party_candidates",
            respondent_party_candidates,
        )

        checkbox_fields = [
            "with_application",
            "hide_party_petitioner",
            "hide_party_respondent",
            "differently_abled_petitioner",
            "differently_abled_respondent",
        ]

        for field_key in checkbox_fields:
            result, _, _ = self._extract_one_field(document_id=document_id, field_key=field_key)
            self._persist_field_result(job.id, document_id, result)
            field_results.append(result)
            extracted_map[field_key] = result

        single_advocate_fields = [
            "advocate_name",
            "advocate_enrol_no",
            "advocate_enrol_year",
            "advocate_mobile",
            "advocate_remark",
        ]

        for field_key in single_advocate_fields:
            result, candidates, _ = self._extract_one_field(document_id=document_id, field_key=field_key)
            if field_key == "advocate_name":
                add_conflict_flag(review_flags, field_key, candidates)
            self._persist_field_result(job.id, document_id, result)
            field_results.append(result)
            extracted_map[field_key] = result

        advocate_rows_context = self.retrieval.build_field_context(
            document_id=document_id, field_key="advocate_rows"
        )
        advocate_row_candidates = self.candidate_extractor.extract_candidates(
            "advocate_rows", advocate_rows_context
        )
        advocate_row_candidates = self.feedback_reranker.adjust_candidate_scores(
            "advocate_rows", advocate_row_candidates
        )
        advocate_rows = build_advocate_rows(advocate_row_candidates, max_rows=2)
        logger.info(
            "[EXTRACTION][advocate_rows] candidates=%s rows=%s",
            len(advocate_row_candidates),
            [
                {
                    "row": r.row_index,
                    "name": r.name,
                    "enrol": r.enrol_no,
                    "mobile": r.mobile,
                    "confidence": round(float(r.confidence), 3),
                }
                for r in advocate_rows
            ],
        )

        petitioner_details_context = self.retrieval.build_field_context(
            document_id=document_id, field_key="petitioner_more_details"
        )
        petitioner_details_candidates = self.candidate_extractor.extract_candidates(
            "petitioner_more_details", petitioner_details_context
        )
        petitioner_more_details = build_party_more_details(petitioner_details_candidates)

        respondent_details_context = self.retrieval.build_field_context(
            document_id=document_id, field_key="respondent_more_details"
        )
        respondent_details_candidates = self.candidate_extractor.extract_candidates(
            "respondent_more_details", respondent_details_context
        )
        respondent_more_details = build_party_more_details(respondent_details_candidates)

        grouped = build_grouped_fields(field_results)
        if "petitioner_name" in grouped.petitioner_fields:
            grouped.petitioner_fields["petitioner_name"].suggestions = build_party_suggestions(
                petitioner_party_candidates,
                max_items=3,
            )
        if "respondent_name" in grouped.respondent_fields:
            grouped.respondent_fields["respondent_name"].suggestions = build_party_suggestions(
                respondent_party_candidates,
                max_items=3,
            )
        grouped.advocate_rows = advocate_rows
        grouped.petitioner_more_details = petitioner_more_details
        grouped.respondent_more_details = respondent_more_details

        self.db.commit()

        confirmed_count = sum(1 for f in field_results if f.status == "confirmed")
        suggested_count = sum(1 for f in field_results if f.status == "suggested")
        missing_count = sum(1 for f in field_results if f.status == "missing")

        confidences = [f.confidence for f in field_results]
        confidences.extend([row.confidence for row in advocate_rows if row.confidence > 0])
        if petitioner_more_details.confidence > 0:
            confidences.append(petitioner_more_details.confidence)
        if respondent_more_details.confidence > 0:
            confidences.append(respondent_more_details.confidence)

        job.overall_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        job.needs_review = suggested_count > 0 or missing_count > 0 or len(review_flags) > 0
        job.status = "needs_review" if job.needs_review else "completed"
        job.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)

        response = ExtractionResponse(
            job=ExtractionJobSummary(
                extraction_job_id=job.id,
                document_id=job.document_id,
                form_type=job.form_type,
                status=job.status,
                extractor_version=job.extractor_version,
                overall_confidence=job.overall_confidence,
                needs_review=job.needs_review,
                started_at=job.started_at,
                completed_at=job.completed_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
            ),
            fields=field_results,
            grouped=grouped,
            confirmed_count=confirmed_count,
            suggested_count=suggested_count,
            missing_count=missing_count,
            review_flags=review_flags,
        )

        page_texts = self._load_page_texts(document_id)
        decision = self.document_type_router.decide(page_texts)
        logger.info(
            "[EXTRACTION][document_type] type=%s confidence=%s reasons=%s priority_pages=%s",
            decision.document_type,
            decision.confidence,
            decision.reasons,
            decision.priority_pages,
        )
        if decision.document_type in {"lower_court_record", "order_sheet_bundle"}:
            lower_court_candidates = LowerCourtExtractor().extract(
                pages=page_texts,
                priority_pages=decision.priority_pages,
            )
            logger.info(
                "[EXTRACTION][lower_court] candidates=%s",
                [candidate.model_dump() for candidate in lower_court_candidates[:8]],
            )
            response = self._merge_lower_court_candidates(
                response=response,
                candidates=lower_court_candidates,
                decision=decision,
                pages=page_texts,
            )
            job.needs_review = True
            job.status = "needs_review"
            self.db.commit()

        v2_candidates, v2_debug = FieldSpecificExtractionService(self.db).extract(document_id)
        response = self._merge_v2_candidates(response, v2_candidates)
        response.review_flags.extend(
            [
                f"v2_candidates:{v2_debug.get('v2_candidates_count', 0)}",
                f"v2_rejected:{v2_debug.get('rejected_candidates_count', 0)}",
                f"v2_page_types:{','.join(v2_debug.get('page_types_used', []))}",
            ]
        )

        return response

    def run_sync(self, document_id: int, payload: ExtractionRunRequest) -> ExtractionResponse:
        job = self.create_job(document_id=document_id, payload=payload)
        return self._run_job(job)

    def run_existing_job(self, extraction_job_id: int) -> ExtractionResponse | None:
        job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.id == extraction_job_id)
            .first()
        )
        if not job:
            return None
        return self._run_job(job)

    def get_latest_result(self, document_id: int) -> ExtractionResponse | None:
        job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.document_id == document_id)
            .order_by(ExtractionJob.id.desc())
            .first()
        )
        if not job:
            return None

        field_rows = (
            self.db.query(ExtractedField)
            .filter(ExtractedField.extraction_job_id == job.id)
            .order_by(ExtractedField.id.asc())
            .all()
        )

        fields = [
            FieldResult(
                field_key=row.field_key,
                field_label=row.field_label,
                status=row.status,
                value=row.raw_value,
                normalized_value=row.normalized_value,
                confidence=row.confidence,
                evidence=FieldEvidence(
                    source_type=row.source_type,
                    page_from=row.source_page_from,
                    page_to=row.source_page_to,
                    chunk_id=row.source_chunk_id,
                    text=row.evidence_text,
                    validation_notes=row.validation_notes,
                ),
                suggestions=[],
            )
            for row in field_rows
        ]

        grouped = build_grouped_fields(fields)

        return ExtractionResponse(
            job=ExtractionJobSummary(
                extraction_job_id=job.id,
                document_id=job.document_id,
                form_type=job.form_type,
                status=job.status,
                extractor_version=job.extractor_version,
                overall_confidence=job.overall_confidence,
                needs_review=job.needs_review,
                started_at=job.started_at,
                completed_at=job.completed_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
            ),
            fields=fields,
            grouped=grouped,
            confirmed_count=sum(1 for f in fields if f.status == "confirmed"),
            suggested_count=sum(1 for f in fields if f.status == "suggested"),
            missing_count=sum(1 for f in fields if f.status == "missing"),
            review_flags=[],
        )


