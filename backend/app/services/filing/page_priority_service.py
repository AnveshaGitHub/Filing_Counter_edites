from __future__ import annotations

import re
from dataclasses import dataclass

"""
Priority scorer for lower-court routing.

This intentionally stays separate from PageClassifierService: it ranks pages
for lower-court title/index/order-sheet workflows and falls back to an existing
page_type when one has already been classified.
"""


@dataclass
class PageText:
    page_no: int
    text: str
    page_type: str | None = None


class PagePriorityService:
    TITLE_HINTS = [
        "title page",
        "name of first plaintiff",
        "name of first appellant",
        "name of first applicant",
        "first defendant",
        "first respondent",
        "suit",
        "appeal",
        "record room",
        "date of decision",
    ]

    INDEX_HINTS = [
        "file-a",
        "file a",
        "list of document",
        "list of documents",
        "index",
        "order sheet",
        "judgment",
    ]

    ORDER_SHEET_HINTS = [
        "order sheet",
        "order or proceeding",
        "signature of presiding officer",
        "date of order",
        "pleaders where necessary",
    ]

    def normalize(self, text: str | None) -> str:
        if not text:
            return ""
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def score_page(self, page: PageText) -> tuple[str, float, list[str]]:
        text = self.normalize(page.text)
        low = text.lower()
        reasons: list[str] = []

        title_score = sum(1 for hint in self.TITLE_HINTS if hint in low)
        index_score = sum(1 for hint in self.INDEX_HINTS if hint in low)
        order_score = sum(1 for hint in self.ORDER_SHEET_HINTS if hint in low)

        if title_score >= 2:
            reasons.append("title_page_hints")
            return "lower_court_title_page", min(1.0, title_score / 4), reasons

        if index_score >= 2:
            reasons.append("index_page_hints")
            return "lower_court_index_page", min(1.0, index_score / 4), reasons

        if order_score >= 2:
            reasons.append("order_sheet_hints")
            return "order_sheet_page", min(1.0, order_score / 4), reasons

        if page.page_type:
            reasons.append(f"existing_type:{page.page_type}")
            return page.page_type, 0.4, reasons

        return "unknown_page", 0.1, reasons

    def get_priority_pages(self, pages: list[PageText]) -> list[int]:
        scored: list[tuple[float, int]] = []
        for page in pages:
            page_type, score, _ = self.score_page(page)
            weight = {
                "lower_court_title_page": 100,
                "lower_court_index_page": 80,
                "body_pleading_page": 50,
                "unknown_page": 20,
                "order_sheet_page": 5,
                "order_copy_page": 5,
            }.get(page_type, 10)

            early_bonus = max(0, 20 - page.page_no)
            scored.append((weight + early_bonus + score, page.page_no))

        scored.sort(reverse=True)
        return [page_no for _, page_no in scored[:10]]
