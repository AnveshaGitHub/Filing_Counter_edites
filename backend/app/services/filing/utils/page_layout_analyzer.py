from __future__ import annotations

from app.services.filing.utils.text_cleaner import normalize_for_matching

"""
Lightweight multi-tag page hints for retrieval and candidate scoring.

This module is not the canonical persisted page classifier. It gives chunks and
retrieval candidates multiple coarse tags so existing confidence multipliers can
continue to work without loading classifier state.
"""

PAGE_TYPES = [
    "scrutiny_page",
    "computer_sheet_page",
    "cause_title_page",
    "index_page",
    "vakalatnama_or_appearance_page",
    "body_pleading_page",
    "annexure_page",
    "order_copy_page",
    "template_case_type_page",
]


def classify_page(text: str | None) -> dict:
    low = normalize_for_matching(text)
    page_types: list[str] = []
    matched_signals: list[str] = []

    def has(*tokens: str) -> bool:
        return any(token in low for token in tokens)

    if has(
        "scrutiny report",
        "checker",
        "subject heading",
        "category/sub-category",
        "court fee",
    ):
        page_types.append("scrutiny_page")
        matched_signals.append("scrutiny")

    if has("computer sheet", "class of case", "name of the main advocate"):
        page_types.append("computer_sheet_page")
        matched_signals.append("computer_sheet")

    if has("in the high court", "versus") and has("applicant", "petitioner", "respondent", "appellant"):
        page_types.append("cause_title_page")
        matched_signals.append("cause_title")

    if has("index", "description of documents", "annexures", "pages"):
        page_types.append("index_page")
        matched_signals.append("index")

    if has(
        "vakalatnama",
        "vakalat nama",
        "memo of appearance",
        "advocate for applicant",
        "counsel for appellant",
        "appearance",
    ):
        page_types.append("vakalatnama_or_appearance_page")
        matched_signals.append("appearance")

    if has("facts of the case", "grounds", "prayer"):
        page_types.append("body_pleading_page")
        matched_signals.append("pleading")

    if has("order sheet", "hon'ble", " before ", "order"):
        page_types.append("order_copy_page")
        matched_signals.append("order")

    if has("document-d/1", "document-a/1", "annexure"):
        page_types.append("annexure_page")
        matched_signals.append("annexure")

    if has("criminal appeal", "criminal revision", "misc. criminal case"):
        page_types.append("template_case_type_page")
        matched_signals.append("case_type_template")

    if not page_types:
        if has("versus", "petitioner", "respondent", "applicant"):
            page_types.append("cause_title_page")
            matched_signals.append("cause_title_soft")
        else:
            page_types.append("body_pleading_page")
            matched_signals.append("default_body")

    return {
        "page_types": page_types,
        "matched_signals": matched_signals,
    }


def page_type_score(page_type: str, field_key: str) -> float:
    if field_key == "case_type":
        weights = {
            "cause_title_page": 1.00,
            "computer_sheet_page": 0.99,
            "index_page": 0.96,
            "scrutiny_page": 0.90,
            "vakalatnama_or_appearance_page": 0.72,
            "body_pleading_page": 0.66,
            "order_copy_page": 0.60,
            "annexure_page": 0.55,
            "template_case_type_page": 0.35,
        }
        return weights.get(page_type, 0.65)

    if field_key in {"petitioner_name", "respondent_name"}:
        weights = {
            "cause_title_page": 1.00,
            "computer_sheet_page": 0.95,
            "index_page": 0.88,
            "vakalatnama_or_appearance_page": 0.72,
            "body_pleading_page": 0.62,
            "scrutiny_page": 0.56,
            "order_copy_page": 0.52,
            "annexure_page": 0.48,
        }
        return weights.get(page_type, 0.62)

    if field_key.startswith("advocate_") or field_key == "advocate_rows":
        weights = {
            "vakalatnama_or_appearance_page": 1.00,
            "computer_sheet_page": 0.95,
            "index_page": 0.86,
            "cause_title_page": 0.74,
            "body_pleading_page": 0.58,
            "order_copy_page": 0.56,
            "scrutiny_page": 0.50,
            "annexure_page": 0.46,
        }
        return weights.get(page_type, 0.60)

    weights = {
        "cause_title_page": 0.90,
        "index_page": 0.88,
        "computer_sheet_page": 0.86,
        "body_pleading_page": 0.76,
        "vakalatnama_or_appearance_page": 0.72,
        "scrutiny_page": 0.68,
        "order_copy_page": 0.62,
        "annexure_page": 0.56,
    }
    return weights.get(page_type, 0.70)


def page_priority_multiplier(page_types: list[str] | None, field_key: str) -> float:
    if not page_types:
        return 0.72
    best = max(page_type_score(page_type, field_key) for page_type in page_types)
    return max(0.45, min(1.0, best))
