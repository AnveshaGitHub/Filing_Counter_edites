from __future__ import annotations

from app.schemas.document_type import DocumentTypeDecision
from app.services.filing.page_priority_service import PagePriorityService, PageText


class DocumentTypeRouterService:
    def __init__(self) -> None:
        self.priority_service = PagePriorityService()

    def decide(self, pages: list[PageText]) -> DocumentTypeDecision:
        if not pages:
            return DocumentTypeDecision(
                document_type="unknown",
                confidence=0.0,
                reasons=["no_pages"],
                priority_pages=[],
            )

        page_types: list[str] = []
        for page in pages:
            page_type, _, _ = self.priority_service.score_page(page)
            page_types.append(page_type)

        total = max(len(page_types), 1)
        order_count = sum(1 for value in page_types if value in {"order_sheet_page", "order_copy_page"})
        title_count = sum(1 for value in page_types if value == "lower_court_title_page")
        index_count = sum(1 for value in page_types if value == "lower_court_index_page")
        priority_pages = self.priority_service.get_priority_pages(pages)

        if title_count > 0 or index_count > 0:
            return DocumentTypeDecision(
                document_type="lower_court_record",
                confidence=0.82,
                reasons=["title_or_index_page_found"],
                priority_pages=priority_pages,
            )

        if order_count / total >= 0.45:
            return DocumentTypeDecision(
                document_type="order_sheet_bundle",
                confidence=0.76,
                reasons=["order_sheet_heavy_pdf"],
                priority_pages=priority_pages,
            )

        return DocumentTypeDecision(
            document_type="filing_form_or_mixed",
            confidence=0.65,
            reasons=["default_current_extractor"],
            priority_pages=priority_pages,
        )
