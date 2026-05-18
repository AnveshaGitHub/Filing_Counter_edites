from __future__ import annotations

from sqlalchemy.orm import Session

from app.integrations.vector_store.chroma_retriever import ChromaRetriever
from app.services.filing.utils.page_layout_analyzer import (
    classify_page,
    page_priority_multiplier,
)
from app.services.filing.utils.text_cleaner import clean_ocr_text


class FilingRetrievalService:
    FIELD_QUERY_HINTS = {
        "case_type": [
            "case type case title criminal revision appeal writ petition heading",
            "first page cause title case heading",
        ],
        "list_type": [
            "list type individual regular urgent",
            "listing bench regular individual urgent",
        ],
        "petitioner_name": [
            "petitioner applicant appellant revisionist cause title versus",
            "party name first page cause title petitioner",
        ],
        "respondent_name": [
            "respondent non-applicant opponent versus cause title",
            "party name first page cause title respondent",
        ],
        "petitioner_party_type": [
            "petitioner applicant state of madhya pradesh union of india department corporation company",
        ],
        "respondent_party_type": [
            "respondent non-applicant state of madhya pradesh union of india department corporation company",
        ],
        "advocate_name": [
            "advocate counsel learned counsel vakalatnama for petitioner for respondent",
            "appearance advocate name counsel",
        ],
        "advocate_enrol_no": [
            "advocate enrol no enrollment no bar registration vakalatnama",
        ],
        "advocate_enrol_year": [
            "advocate enrol year year of enrolment vakalatnama",
        ],
        "advocate_mobile": [
            "advocate mobile contact phone vakalatnama",
        ],
        "with_application": [
            "with application interlocutory application ia no",
        ],
        "hide_party_petitioner": [
            "identity protection hide party sealed confidential",
        ],
        "hide_party_respondent": [
            "identity protection hide party sealed confidential",
        ],
        "differently_abled_petitioner": [
            "differently abled disability divyang handicap petitioner",
        ],
        "differently_abled_respondent": [
            "differently abled disability divyang handicap respondent",
        ],
        "advocate_rows": [
            "advocate counsel vakalatnama appearance enrol no mobile",
            "for petitioner for respondent advocate details",
        ],
        "petitioner_more_details": [
            "petitioner address district state pincode mobile email",
        ],
        "respondent_more_details": [
            "respondent address district state pincode mobile email",
        ],
        "petitioner_party_candidates": [
            "petitioner applicant appellant revisionist cause title versus parties",
        ],
        "respondent_party_candidates": [
            "respondent non applicant opposite party cause title versus parties",
        ],
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.vector_retriever = ChromaRetriever()

    def _get_document_pages(self, document_id: int) -> list[dict]:
        # Primary source: main document page model
        try:
            from app.models.document_page import DocumentPage

            rows = (
                self.db.query(DocumentPage)
                .filter(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_no.asc())
                .all()
            )
            if rows:
                result: list[dict] = []
                for row in rows:
                    text = clean_ocr_text(getattr(row, "ocr_text", None))
                    meta = classify_page(text)
                    result.append(
                        {
                            "page_no": row.page_no,
                            "text": text,
                            "ocr_confidence": getattr(row, "ocr_confidence", None),
                            "page_types": meta["page_types"],
                            "layout_signals": meta["matched_signals"],
                        }
                    )
                return result
        except Exception:
            pass

        # Fallback source: local standalone testing tables
        try:
            from app.models.local_test_document_page import LocalTestDocumentPage

            rows = (
                self.db.query(LocalTestDocumentPage)
                .filter(LocalTestDocumentPage.document_id == document_id)
                .order_by(LocalTestDocumentPage.page_no.asc())
                .all()
            )
            result: list[dict] = []
            for row in rows:
                text = clean_ocr_text(getattr(row, "ocr_text", None))
                meta = classify_page(text)
                result.append(
                    {
                        "page_no": row.page_no,
                        "text": text,
                        "ocr_confidence": getattr(row, "ocr_confidence", None),
                        "page_types": meta["page_types"],
                        "layout_signals": meta["matched_signals"],
                    }
                )
            return result
        except Exception:
            return []

    def _get_index_rows(self, document_id: int) -> list[dict]:
        model_candidates = []

        try:
            from app.models.document_index import DocumentIndex

            model_candidates.append(DocumentIndex)
        except Exception:
            pass

        try:
            from app.models.index_row import IndexRow

            model_candidates.append(IndexRow)
        except Exception:
            pass

        try:
            from app.models.document_section import DocumentSection

            model_candidates.append(DocumentSection)
        except Exception:
            pass

        for model in model_candidates:
            try:
                order_attr = getattr(model, "page_from", None) or getattr(model, "from_page")
                rows = (
                    self.db.query(model)
                    .filter(model.document_id == document_id)
                    .order_by(order_attr.asc())
                    .all()
                )

                result: list[dict] = []
                for row in rows:
                    title = getattr(row, "title", None) or getattr(row, "section_title", None)
                    meta = classify_page(clean_ocr_text(title))
                    result.append(
                        {
                            "title": title,
                            "page_from": getattr(row, "page_from", None)
                            or getattr(row, "from_page", None),
                            "page_to": getattr(row, "page_to", None) or getattr(row, "to_page", None),
                            "doc_type": getattr(row, "doc_type", None),
                            "page_types": meta["page_types"],
                        }
                    )
                if result:
                    return result
            except Exception:
                continue

        return []

    def _filter_index_rows_for_field(self, index_rows: list[dict], field_key: str) -> list[dict]:
        if field_key.startswith("advocate_"):
            return [
                row
                for row in index_rows
                if any(
                    token in (str(row.get("title") or "").lower())
                    for token in ["advocate", "vakalat", "counsel", "appearance"]
                )
            ]

        if field_key in {
            "petitioner_name",
            "respondent_name",
            "petitioner_party_type",
            "respondent_party_type",
            "petitioner_party_candidates",
            "respondent_party_candidates",
        }:
            return [
                row
                for row in index_rows
                if any(
                    token in (str(row.get("title") or "").lower())
                    for token in ["cause", "title", "party", "petitioner", "respondent", "applicant"]
                )
            ]

        return index_rows

    def _get_priority_pages(self, all_pages: list[dict], field_key: str) -> list[dict]:
        if field_key.startswith("advocate_") or field_key == "advocate_rows":
            base = [p for p in all_pages if p["page_no"] <= 15]
            boosted = [
                p
                for p in all_pages
                if page_priority_multiplier(p.get("page_types"), field_key) >= 0.9
            ]
            return sorted({p["page_no"]: p for p in (base + boosted)}.values(), key=lambda x: x["page_no"])

        if field_key in {"petitioner_more_details", "respondent_more_details"}:
            return [p for p in all_pages if p["page_no"] <= 15]

        if field_key in {
            "with_application",
            "hide_party_petitioner",
            "hide_party_respondent",
            "differently_abled_petitioner",
            "differently_abled_respondent",
        }:
            return [p for p in all_pages if p["page_no"] <= 10]

        if field_key in {
            "case_type",
            "list_type",
            "petitioner_name",
            "respondent_name",
            "petitioner_party_type",
            "respondent_party_type",
            "petitioner_party_candidates",
            "respondent_party_candidates",
        }:
            base = [p for p in all_pages if p["page_no"] <= 6]
            boosted = [
                p
                for p in all_pages
                if page_priority_multiplier(p.get("page_types"), field_key) >= 0.9
            ]
            return sorted({p["page_no"]: p for p in (base + boosted)}.values(), key=lambda x: x["page_no"])

        return [p for p in all_pages if p["page_no"] <= 10]

    def _run_vector_queries(self, document_id: int, field_key: str) -> list[dict]:
        results: list[dict] = []
        queries = self.FIELD_QUERY_HINTS.get(field_key, [])
        for query in queries:
            hits = self.vector_retriever.search_document(document_id=document_id, query=query, top_k=8)
            for hit in hits:
                results.append(
                    {
                        "chunk_id": hit.get("chunk_id"),
                        "text": clean_ocr_text(hit.get("text")),
                        "page_no": hit.get("page_no"),
                        "score": hit.get("score"),
                        "metadata": hit.get("metadata", {}),
                    }
                )
        return results

    def build_field_context(
        self,
        document_id: int,
        field_key: str,
        linked_name_value: str | None = None,
        linked_name_evidence: dict | None = None,
    ) -> dict:
        all_pages = self._get_document_pages(document_id=document_id)
        priority_pages = self._get_priority_pages(all_pages, field_key=field_key)
        raw_index_rows = self._get_index_rows(document_id=document_id)
        index_rows = self._filter_index_rows_for_field(raw_index_rows, field_key=field_key)
        candidate_chunks = self._run_vector_queries(document_id=document_id, field_key=field_key)
        page_type_map = {p.get("page_no"): p.get("page_types", []) for p in all_pages}

        for chunk in candidate_chunks:
            chunk["page_types"] = page_type_map.get(chunk.get("page_no"), [])
        for row in index_rows:
            if not row.get("page_types"):
                row["page_types"] = page_type_map.get(row.get("page_from"), [])

        return {
            "document_id": document_id,
            "field_key": field_key,
            "all_pages": all_pages,
            "candidate_pages": priority_pages,
            "candidate_chunks": candidate_chunks,
            "index_rows": index_rows,
            "page_type_map": page_type_map,
            "page_hints": [p["page_no"] for p in priority_pages],
            "linked_name_value": linked_name_value,
            "linked_name_evidence": linked_name_evidence,
        }
