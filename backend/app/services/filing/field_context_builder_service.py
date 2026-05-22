from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.services.filing.field_page_router_service import FIELD_RULES, FieldPageRouterService
from app.services.filing.filing_retrieval_service import FilingRetrievalService
from app.services.filing.page_classifier_service import PageInput
from app.services.filing.routed_region_extractor_service import (
    FIELD_GROUP_TO_REGION,
    RoutedRegionExtractorService,
)

logger = logging.getLogger(__name__)


FIELD_TO_GROUP: dict[str, str] = {
    "case_type": "case_type",
    "list_type": "list_type",
    "petitioner_name": "petitioner_name",
    "petitioner_party_type": "petitioner_details",
    "petitioner_relation": "petitioner_details",
    "petitioner_father_or_husband": "petitioner_details",
    "petitioner_age": "petitioner_details",
    "petitioner_occupation": "petitioner_details",
    "petitioner_address": "petitioner_details",
    "petitioner_state": "petitioner_details",
    "petitioner_district": "petitioner_details",
    "petitioner_tehsil": "tehsil",
    "petitioner_village": "village",
    "petitioner_party_candidates": "petitioner_name",
    "petitioner_more_details": "petitioner_details",
    "respondent_name": "respondent_name",
    "respondent_party_type": "respondent_details",
    "respondent_relation": "respondent_details",
    "respondent_father_or_husband": "respondent_details",
    "respondent_age": "respondent_details",
    "respondent_occupation": "respondent_details",
    "respondent_address": "respondent_details",
    "respondent_state": "respondent_details",
    "respondent_district": "respondent_details",
    "respondent_tehsil": "tehsil",
    "respondent_village": "village",
    "respondent_party_candidates": "respondent_name",
    "respondent_more_details": "respondent_details",
    "advocate_name": "advocate_name",
    "advocate_enrol_no": "advocate_enrol_no",
    "advocate_enrol_year": "advocate_enrol_year",
    "advocate_mobile": "advocate_name",
    "advocate_remark": "advocate_name",
    "advocate_rows": "advocate_name",
    "police_station": "police_station",
    "crime_no": "crime_no",
    "crime_year": "crime_year",
    "district": "district",
    "tehsil": "tehsil",
    "village": "village",
    "lower_court_case_no": "lower_court_case_no",
    "lower_court_case_year": "lower_court_case_year",
    "cnr_no": "cnr_no",
    "judge_name": "judge_name",
    "impugned_judgment_date": "impugned_order_date",
    "impugned_order_date": "impugned_order_date",
    "subject_code": "subject_category",
    "category_code": "subject_category",
    "sub_category_code": "subject_category",
    "subject_category": "subject_category",
    "provision_of_law": "provision_of_law",
    "limitation_dates": "limitation_dates",
    "ia_details": "ia_details",
    "document_index": "document_index",
}


FIELD_TO_REGION_GROUP: dict[str, str] = {
    "petitioner_name": "petitioner_name",
    "petitioner_party_type": "petitioner_details",
    "petitioner_relation": "petitioner_details",
    "petitioner_father_or_husband": "petitioner_details",
    "petitioner_age": "petitioner_details",
    "petitioner_occupation": "petitioner_details",
    "petitioner_address": "petitioner_details",
    "petitioner_state": "petitioner_details",
    "petitioner_district": "petitioner_details",
    "petitioner_tehsil": "petitioner_details",
    "petitioner_village": "petitioner_details",
    "petitioner_party_candidates": "petitioner_name",
    "petitioner_more_details": "petitioner_details",
    "respondent_name": "respondent_name",
    "respondent_party_type": "respondent_details",
    "respondent_relation": "respondent_details",
    "respondent_father_or_husband": "respondent_details",
    "respondent_age": "respondent_details",
    "respondent_occupation": "respondent_details",
    "respondent_address": "respondent_details",
    "respondent_state": "respondent_details",
    "respondent_district": "respondent_details",
    "respondent_tehsil": "respondent_details",
    "respondent_village": "respondent_details",
    "respondent_party_candidates": "respondent_name",
    "respondent_more_details": "respondent_details",
    "advocate_name": "advocate_details",
    "advocate_enrol_no": "advocate_details",
    "advocate_enrol_year": "advocate_details",
    "advocate_mobile": "advocate_details",
    "advocate_remark": "advocate_details",
    "advocate_rows": "advocate_details",
    "police_station": "fir_details",
    "crime_no": "fir_details",
    "crime_year": "fir_details",
    "lower_court_case_no": "lower_court_details",
    "lower_court_case_year": "lower_court_details",
    "lower_court_district": "lower_court_details",
    "cnr_no": "lower_court_details",
    "judge_name": "lower_court_details",
    "impugned_judgment_date": "lower_court_details",
    "impugned_order_date": "lower_court_details",
    "subject_code": "subject_category",
    "category_code": "subject_category",
    "sub_category_code": "subject_category",
    "subject_category": "subject_category",
    "provision_of_law": "subject_category",
    "limitation_dates": "limitation_dates",
    "ia_details": "ia_details",
    "document_index": "document_index",
}


class FieldContextBuilderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retrieval = FilingRetrievalService(db)
        self.router = FieldPageRouterService(db)
        self.region_extractor = RoutedRegionExtractorService(db)

    def build_field_context(
        self,
        document_id: int,
        field_key: str,
        linked_name_value: str | None = None,
        linked_name_evidence: dict | None = None,
    ) -> dict:
        fallback_context = self.retrieval.build_field_context(
            document_id=document_id,
            field_key=field_key,
            linked_name_value=linked_name_value,
            linked_name_evidence=linked_name_evidence,
        )
        group = self.field_group_for(field_key)
        region_group = self.region_group_for(field_key)
        region_pages = self._safe_region_pages(document_id=document_id, field_group=region_group)
        if region_pages:
            routed_chunks = [
                {
                    "chunk_id": f"region_{document_id}_{page['page_no']}_{idx}",
                    "text": page.get("text") or "",
                    "page_no": page.get("page_no"),
                    "score": page.get("region_score"),
                    "metadata": {"source": "routed_region", "field_group": region_group},
                    "page_types": page.get("page_types", []),
                    "route_reasons": page.get("route_reasons", []),
                }
                for idx, page in enumerate(region_pages)
            ]
            context = dict(fallback_context)
            context["candidate_pages"] = region_pages
            context["candidate_chunks"] = routed_chunks
            context["page_hints"] = [page["page_no"] for page in region_pages if page.get("page_no")]
            context["route_group"] = group
            context["region_group"] = region_group
            context["route_applied"] = True
            context["region_applied"] = True
            context["route_debug"] = [
                {
                    "page_no": page.get("page_no"),
                    "route_score": page.get("route_score"),
                    "region_score": page.get("region_score"),
                    "region_type": page.get("region_type"),
                    "reasons": page.get("route_reasons", []),
                }
                for page in region_pages
            ]
            return context

        routed_pages = self._safe_context_pages(document_id=document_id, field_group=group)
        if not routed_pages:
            fallback_context["route_group"] = group
            fallback_context["region_group"] = region_group
            fallback_context["route_applied"] = False
            fallback_context["region_applied"] = False
            return fallback_context

        routed_chunks = [
            {
                "chunk_id": f"route_{document_id}_{page['page_no']}",
                "text": page.get("text") or "",
                "page_no": page.get("page_no"),
                "score": page.get("route_score"),
                "metadata": {"source": "field_router", "field_group": group},
                "page_types": page.get("page_types", []),
                "route_reasons": page.get("route_reasons", []),
            }
            for page in routed_pages
        ]

        context = dict(fallback_context)
        context["candidate_pages"] = routed_pages
        context["candidate_chunks"] = routed_chunks
        context["page_hints"] = [page["page_no"] for page in routed_pages]
        context["route_group"] = group
        context["region_group"] = region_group
        context["route_applied"] = True
        context["region_applied"] = False
        context["route_debug"] = [
            {
                "page_no": page.get("page_no"),
                "score": page.get("route_score"),
                "matched_keywords": page.get("matched_keywords", []),
                "negative_keywords": page.get("negative_keywords", []),
                "region_type": page.get("region_type"),
            }
            for page in routed_pages
        ]
        return context

    def build_text_context(
        self,
        document_id: int,
        field_key: str,
        fallback_text: str = "",
        max_chars: int = 9000,
    ) -> str:
        try:
            group = self.region_group_for(field_key)
            routed = self.region_extractor.get_context(
                document_id=document_id,
                field_group=group,
                max_chars=max_chars,
            )
            return routed or fallback_text
        except Exception:
            logger.exception("[FIELD CONTEXT] routed region text context failed")
            return fallback_text

    def build_pages_for_fields(
        self,
        document_id: int,
        field_keys: set[str],
        fallback_pages: list[PageInput],
    ) -> list[PageInput]:
        page_map = {page.page_no: page for page in fallback_pages}
        selected_region_pages: list[PageInput] = []
        selected_page_nos: list[int] = []
        for field_key in field_keys:
            region_group = self.region_group_for(field_key)
            for idx, page in enumerate(self._safe_region_pages(document_id=document_id, field_group=region_group, max_regions=4)):
                page_no = int(page.get("page_no") or 0)
                text = str(page.get("text") or "")
                if text.strip():
                    selected_region_pages.append(PageInput(page_no=page_no or idx + 1, text=text))
                    if page_no:
                        selected_page_nos.append(page_no)

            if selected_region_pages:
                continue

            group = self.field_group_for(field_key)
            for page in self._safe_context_pages(document_id=document_id, field_group=group, max_pages=4):
                page_no = int(page.get("page_no") or 0)
                if page_no and page_no not in selected_page_nos:
                    selected_page_nos.append(page_no)

        if selected_region_pages:
            return selected_region_pages

        if not selected_page_nos:
            return fallback_pages

        routed = [page_map[page_no] for page_no in selected_page_nos if page_no in page_map]
        return routed or fallback_pages

    def field_group_for(self, field_key: str) -> str:
        group = FIELD_TO_GROUP.get(field_key, field_key)
        return group if group in FIELD_RULES else field_key

    def region_group_for(self, field_key: str) -> str:
        group = FIELD_TO_REGION_GROUP.get(field_key) or FIELD_TO_GROUP.get(field_key, field_key)
        if group in FIELD_GROUP_TO_REGION:
            return group
        return field_key if field_key in FIELD_GROUP_TO_REGION else group

    def _safe_context_pages(
        self,
        document_id: int,
        field_group: str,
        max_pages: int = 5,
    ) -> list[dict]:
        try:
            return self.router.get_context_pages(
                document_id=document_id,
                field_key=field_group,
                max_pages=max_pages,
            )
        except Exception:
            logger.exception("[FIELD CONTEXT] route lookup failed field_group=%s", field_group)
            return []

    def _safe_region_pages(
        self,
        document_id: int,
        field_group: str,
        max_regions: int = 5,
    ) -> list[dict]:
        try:
            return self.region_extractor.get_region_pages(
                document_id=document_id,
                field_group=field_group,
                max_regions=max_regions,
            )
        except Exception:
            logger.exception("[FIELD CONTEXT] region lookup failed field_group=%s", field_group)
            return []
