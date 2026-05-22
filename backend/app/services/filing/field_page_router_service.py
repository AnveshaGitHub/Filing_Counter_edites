from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.services.filing.page_classifier_service import PageClassifierService
from app.services.filing.utils.page_layout_analyzer import classify_page
from app.services.filing.utils.text_cleaner import clean_ocr_text

logger = logging.getLogger(__name__)

ROUTING_DIR = Path("storage/routing")


FIELD_RULES: dict[str, dict[str, list[str]]] = {
    "case_type": {
        "positive": ["case type", "case no", "mcrc", "cra", "crr", "fa", "ma", "wp", "misc. criminal case", "criminal appeal", "first appeal", "प्रकरण", "मामला", "अपील"],
        "structural": ["in the high court", "versus", "vs.", "v/s", "बनाम"],
        "detail": [],
        "negative": ["court fee", "index", "annexure", "fee type"],
    },
    "list_type": {
        "positive": ["urgent", "regular", "admission", "orders", "motion hearing", "listing"],
        "structural": ["list type", "bench", "hearing"],
        "detail": [],
        "negative": ["court fee", "index"],
    },
    "petitioner_name": {
        "positive": ["applicant", "applicants", "petitioner", "petitioners", "appellant", "appellants", "revisionist", "accused", "आवेदक", "याचिकाकर्ता", "अपीलार्थी"],
        "structural": ["versus", "vs.", "v/s", "respondent", "प्रतिवादी", "अनावेदक", "बनाम"],
        "detail": ["s/o", "w/o", "d/o", "aged", "age", "occupation", "r/o", "resident", "जिला", "तहसील", "ग्राम"],
        "negative": ["subject heading", "provision of law", "category/sub-category", "court fee", "index", "list of documents", "fir", "statement", "witness"],
    },
    "respondent_name": {
        "positive": ["respondent", "non-applicant", "non applicant", "state of", "प्रतिवादी", "अनावेदक", "विरुद्ध"],
        "structural": ["versus", "vs.", "v/s", "बनाम"],
        "detail": ["through police station", "p.s.", "police station", "district", "r/o"],
        "negative": ["subject heading", "provision of law", "category/sub-category", "court fee", "index", "list of documents"],
    },
    "petitioner_details": {
        "positive": ["applicant", "appellant", "petitioner", "revisionist", "आवेदक", "अपीलार्थी", "याचिकाकर्ता"],
        "structural": ["versus", "vs.", "respondent", "प्रतिवादी", "अनावेदक"],
        "detail": ["s/o", "w/o", "d/o", "aged", "age", "occupation", "r/o", "resident", "village", "tehsil", "district", "state", "पिता", "पत्नी", "उम्र", "निवासी", "ग्राम", "तहसील", "जिला"],
        "negative": ["subject heading", "provision of law", "category/sub-category", "court fee", "index", "list of documents", "fir", "statement", "witness"],
    },
    "respondent_details": {
        "positive": ["respondent", "non-applicant", "non applicant", "opposite party", "state of", "प्रतिवादी", "अनावेदक"],
        "structural": ["versus", "vs.", "विरुद्ध", "बनाम"],
        "detail": ["through police station", "p.s.", "police station", "district", "r/o", "resident"],
        "negative": ["subject heading", "provision of law", "category/sub-category", "court fee", "index", "list of documents"],
    },
    "advocate_name": {
        "positive": ["advocate", "counsel", "learned counsel", "government advocate", "अधिवक्ता", "वकील"],
        "structural": ["for applicant", "for appellant", "for petitioner", "appearance", "vakalatnama"],
        "detail": ["enrol", "enrollment", "mobile", "email"],
        "negative": ["subject heading", "provision of law", "court fee"],
    },
    "advocate_enrol_no": {
        "positive": ["advocate", "enrol", "enrollment", "enrolment", "bar registration", "अधिवक्ता"],
        "structural": ["vakalatnama", "memo of appearance"],
        "detail": ["no.", "number", "year"],
        "negative": ["subject heading", "provision of law", "court fee"],
    },
    "advocate_enrol_year": {
        "positive": ["advocate", "enrol", "enrollment", "enrolment", "year", "अधिवक्ता"],
        "structural": ["vakalatnama", "memo of appearance"],
        "detail": ["no.", "number", "year"],
        "negative": ["subject heading", "provision of law", "court fee"],
    },
    "crime_no": {
        "positive": ["crime no", "crime number", "fir no", "fir number", "अपराध क्रमांक", "अपराध क्र", "प्रकरण क्रमांक"],
        "structural": ["fir", "first information report", "police station", "थाना"],
        "detail": ["u/s", "section", "धारा"],
        "negative": ["index", "list of documents", "advocate"],
    },
    "crime_year": {
        "positive": ["crime year", "fir year", "crime no", "fir no", "अपराध वर्ष", "अपराध क्रमांक"],
        "structural": ["fir", "police station", "थाना"],
        "detail": ["u/s", "section", "धारा"],
        "negative": ["index", "list of documents", "advocate"],
    },
    "police_station": {
        "positive": ["police station", "p.s.", "ps ", "थाना", "पुलिस थाना"],
        "structural": ["crime no", "fir no", "अपराध क्रमांक"],
        "detail": ["district", "जिला"],
        "negative": ["index", "list of documents", "advocate"],
    },
    "district": {
        "positive": ["district", "जिला"],
        "structural": ["r/o", "resident", "police station", "tehsil", "village"],
        "detail": ["state", "मध्य प्रदेश"],
        "negative": ["court fee", "index"],
    },
    "tehsil": {
        "positive": ["tehsil", "तहसील"],
        "structural": ["r/o", "resident", "village", "district"],
        "detail": ["ग्राम", "जिला"],
        "negative": ["court fee", "index"],
    },
    "village": {
        "positive": ["village", "gram", "ग्राम"],
        "structural": ["r/o", "resident", "tehsil", "district"],
        "detail": ["तहसील", "जिला"],
        "negative": ["court fee", "index"],
    },
    "lower_court_case_no": {
        "positive": ["case no", "criminal case no", "st no", "sessions trial", "lower court", "trial court"],
        "structural": ["impugned order", "judgment", "learned trial court", "sessions judge", "district court", "cnr", "आदेश", "निर्णय", "न्यायालय", "जिला न्यायालय"],
        "detail": [],
        "negative": ["high court header", "index"],
    },
    "lower_court_case_year": {
        "positive": ["case year", "case no", "criminal case no", "st no", "sessions trial"],
        "structural": ["impugned order", "judgment", "learned trial court", "sessions judge", "district court", "cnr", "आदेश", "निर्णय", "न्यायालय"],
        "detail": [],
        "negative": ["high court header", "index"],
    },
    "cnr_no": {
        "positive": ["cnr", "c n r", "case no"],
        "structural": ["district court", "trial court", "न्यायालय"],
        "detail": [],
        "negative": ["high court header", "index"],
    },
    "judge_name": {
        "positive": ["judge", "presiding officer", "sessions judge", "judicial magistrate", "learned judge", "न्यायाधीश"],
        "structural": ["impugned order", "judgment", "order dated", "निर्णय", "आदेश"],
        "detail": [],
        "negative": ["index"],
    },
    "impugned_order_date": {
        "positive": ["impugned order", "impugned judgment", "order dated", "judgment dated", "award dated", "आक्षेपित आदेश", "निर्णय दिनांक", "आदेश दिनांक"],
        "structural": ["learned trial court", "sessions judge", "district court", "न्यायालय"],
        "detail": [],
        "negative": ["court fee", "index"],
    },
    "provision_of_law": {
        "positive": ["provision of law", "act / section", "act/section", "section", "under section", "u/s", "धारा", "अधिनियम"],
        "structural": ["subject heading", "category/sub-category"],
        "detail": [],
        "negative": ["applicant details", "respondent details", "index", "court fee"],
    },
    "subject_category": {
        "positive": ["subject heading", "category/sub-category", "subject/category", "category", "sub-category", "criminal law", "family matters", "motor accident", "commercial courts"],
        "structural": ["scrutiny report", "provision of law"],
        "detail": [],
        "negative": ["applicant details", "respondent details", "index", "court fee"],
    },
    "limitation_dates": {
        "positive": ["limitation", "date of order", "date of filing", "copying date", "delivery ready", "within time", "period of limitation"],
        "structural": ["delay", "certified copy", "filing"],
        "detail": [],
        "negative": ["index"],
    },
    "ia_details": {
        "positive": ["interlocutory application", "ia no", "i.a.", "extension of time", "application", "pending"],
        "structural": ["relief", "prayer"],
        "detail": [],
        "negative": ["court fee"],
    },
    "document_index": {
        "positive": ["index", "list of documents", "description of documents", "document", "page no", "annexure"],
        "structural": ["s.no", "serial no"],
        "detail": [],
        "negative": ["subject heading", "court fee"],
    },
}

FIELD_GROUP_RULES = FIELD_RULES


FIELD_ALIASES: dict[str, str] = {
    "advocate_details": "advocate_name",
    "fir_details": "crime_no",
    "lower_court_details": "lower_court_case_no",
    "impugned_order_details": "impugned_order_date",
}


@dataclass
class PageRoute:
    page_no: int
    score: float
    matched_keywords: list[str]
    negative_keywords: list[str]
    region_type: str | None
    text_excerpt: str
    reasons: list[str]

    @property
    def text_preview(self) -> str:
        return self.text_excerpt


class FieldPageRouterService:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = PageClassifierService()
        ROUTING_DIR.mkdir(parents=True, exist_ok=True)

    def build_routes(self, document_id: int, max_pages_per_field: int = 5) -> dict[str, Any]:
        pages = self._load_pages(document_id)
        routes: dict[str, Any] = {"document_id": document_id, "routes": {}}

        for field_key in FIELD_RULES:
            scored = [self._score_page(field_key, page) for page in pages]
            scored = [item for item in scored if item.score > 0]
            scored.sort(key=lambda item: item.score, reverse=True)
            routes["routes"][field_key] = [asdict(item) for item in scored[:max_pages_per_field]]

        for alias, target in FIELD_ALIASES.items():
            routes["routes"][alias] = routes["routes"].get(target, [])

        self._save_routes(document_id, routes)
        return routes

    def get_routes(self, document_id: int) -> dict[str, Any]:
        path = self._route_path(document_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("[FIELD ROUTER] failed to read cached routes")
        return self.build_routes(document_id)

    def get_route_for_field(self, document_id: int, field_key: str) -> dict[str, Any]:
        resolved = FIELD_ALIASES.get(field_key, field_key)
        routes = self.get_routes(document_id)
        return {
            "document_id": document_id,
            "field_key": field_key,
            "resolved_field_key": resolved,
            "selected_pages": routes.get("routes", {}).get(resolved, []),
        }

    def get_route_for_group(self, document_id: int, field_group: str) -> dict[str, Any]:
        return self.get_route_for_field(document_id=document_id, field_key=field_group)

    def get_context_pages(self, document_id: int, field_key: str, max_pages: int = 5) -> list[dict[str, Any]]:
        route = self.get_route_for_field(document_id, field_key)
        selected = route.get("selected_pages", [])[:max_pages]
        if not selected:
            return []

        page_map = {page["page_no"]: page for page in self._load_pages(document_id)}
        out: list[dict[str, Any]] = []
        for item in selected:
            page = page_map.get(int(item.get("page_no") or 0))
            if not page:
                continue
            text = page.get("clean_text") or page.get("ocr_text") or ""
            if not text.strip():
                continue
            meta = classify_page(text)
            out.append(
                {
                    "page_no": page["page_no"],
                    "text": text,
                    "ocr_confidence": page.get("ocr_confidence"),
                    "page_types": meta.get("page_types", []),
                    "layout_signals": meta.get("matched_signals", []),
                    "route_score": item.get("score"),
                    "route_reasons": item.get("reasons", []),
                    "matched_keywords": item.get("matched_keywords", []),
                    "negative_keywords": item.get("negative_keywords", []),
                    "region_type": item.get("region_type"),
                }
            )
        return out

    def get_context(self, document_id: int, field_key: str, max_chars: int = 9000) -> str:
        chunks: list[str] = []
        for page in self.get_context_pages(document_id, field_key):
            chunks.append(
                f"\n--- PAGE {page['page_no']} | route_score={page.get('route_score')} ---\n{page.get('text') or ''}"
            )
            if sum(len(chunk) for chunk in chunks) >= max_chars:
                break
        return "\n".join(chunks)[:max_chars]

    def _load_pages(self, document_id: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for module_name, class_name in (
            ("app.models.local_test_document_page", "LocalTestDocumentPage"),
            ("app.models.document_page", "DocumentPage"),
        ):
            try:
                module = __import__(module_name, fromlist=[class_name])
                model = getattr(module, class_name)
                query = (
                    self.db.query(model)
                    .filter(model.document_id == document_id)
                    .order_by(model.page_no.asc())
                )
                for row in query.all():
                    text = clean_ocr_text(getattr(row, "ocr_text", "") or "")
                    page_type = getattr(row, "page_type", None) or getattr(row, "detected_page_type", None)
                    if not page_type:
                        page_type = self.classifier.classify_text(getattr(row, "page_no", 0), text).page_type
                    rows.append(
                        {
                            "page_no": int(getattr(row, "page_no", 0) or 0),
                            "ocr_text": text,
                            "clean_text": clean_ocr_text(getattr(row, "clean_text", None) or getattr(row, "ocr_clean_text", None) or "") or text,
                            "page_type": page_type,
                            "ocr_confidence": float(
                                getattr(row, "ocr_avg_confidence", None)
                                or getattr(row, "ocr_confidence", None)
                                or 0.0
                            ),
                            "regions_json": getattr(row, "page_regions_json", None),
                        }
                    )
                if rows:
                    return rows
            except Exception:
                rows = []

        for table in ("local_test_document_pages", "document_pages", "test_document_pages", "pages"):
            try:
                result = self.db.execute(
                    sql_text(
                        f"""
                        SELECT page_no, ocr_text, ocr_confidence, page_regions_json
                        FROM {table}
                        WHERE document_id = :document_id
                        ORDER BY page_no ASC
                        """
                    ),
                    {"document_id": document_id},
                )
                for row in result:
                    text = clean_ocr_text(row[1] or "")
                    rows.append(
                        {
                            "page_no": int(row[0] or 0),
                            "ocr_text": text,
                            "clean_text": text,
                            "page_type": self.classifier.classify_text(int(row[0] or 0), text).page_type,
                            "ocr_confidence": float(row[2] or 0.0),
                            "regions_json": row[3] or "",
                        }
                    )
                if rows:
                    return rows
            except Exception:
                rows = []
        return rows

    def _score_page(self, field_key: str, page: dict[str, Any]) -> PageRoute:
        rules = FIELD_RULES[field_key]
        text = page.get("clean_text") or page.get("ocr_text") or ""
        normalized = self._normalize(text)
        title_text = normalized[:600]
        matched: list[str] = []
        negatives: list[str] = []
        reasons: list[str] = []
        score = 0.0

        for keyword in rules.get("positive", []):
            if self._contains(normalized, keyword):
                score += 1.0
                matched.append(keyword)
        for keyword in rules.get("structural", []):
            if self._contains(normalized, keyword):
                score += 0.75
                matched.append(keyword)
                reasons.append(f"structural:{keyword}")
        for keyword in rules.get("detail", []):
            if self._contains(normalized, keyword):
                score += 0.45
                matched.append(keyword)
        for keyword in rules.get("negative", []):
            if self._contains(normalized, keyword):
                score -= 1.15
                negatives.append(keyword)

        title_hits = [keyword for keyword in rules.get("positive", []) if self._contains(title_text, keyword)]
        if title_hits:
            score += min(1.5, len(title_hits) * 0.35)
            reasons.append("page_title_match")

        region_type, region_score, region_reasons = self._score_regions(field_key, page.get("regions_json"))
        score += region_score
        reasons.extend(region_reasons)

        page_type = str(page.get("page_type") or "").lower()
        if self._page_type_matches(field_key, page_type):
            score += 1.1
            reasons.append(f"page_type:{page_type}")
        elif page_type in {"legal_provision_noise", "metadata_noise", "blank_or_low_text"}:
            score -= 0.85
            reasons.append(f"weak_page_type:{page_type}")

        confidence = float(page.get("ocr_confidence") or 0.0)
        if confidence >= 0.75:
            score += 0.45
            reasons.append("high_ocr_confidence")
        elif 0 < confidence < 0.45:
            score -= 0.55
            reasons.append("low_ocr_confidence")

        if field_key == "case_type" and int(page.get("page_no") or 0) == 1:
            score += 0.35
            reasons.append("page_1_case_type_boost")

        score = max(score, 0.0)
        normalized_score = round(min(score / 8.0, 1.0), 4)
        return PageRoute(
            page_no=int(page.get("page_no") or 0),
            score=normalized_score,
            matched_keywords=matched[:20],
            negative_keywords=negatives[:12],
            region_type=region_type,
            text_excerpt=self._excerpt(text, [*matched, *negatives]),
            reasons=reasons[:16],
        )

    def _score_regions(self, field_key: str, raw_regions: Any) -> tuple[str | None, float, list[str]]:
        regions = self._parse_json(raw_regions)
        best_type: str | None = None
        score = 0.0
        reasons: list[str] = []
        if not isinstance(regions, list):
            return None, score, reasons

        useful = self._useful_region_types(field_key)
        for region in regions:
            if not isinstance(region, dict):
                continue
            region_type = str(region.get("region_type") or region.get("type") or "").lower()
            if not region_type:
                continue
            if region_type == "metadata_noise":
                score -= 0.6
                reasons.append("region:metadata_noise")
            if region_type in {"fee_table"} and field_key != "document_index":
                score -= 0.35
                reasons.append(f"weak_region:{region_type}")
            if region_type in useful:
                score += 0.65
                best_type = region_type
                reasons.append(f"region:{region_type}")
        return best_type, score, reasons

    def _useful_region_types(self, field_key: str) -> set[str]:
        if field_key in {"petitioner_name", "petitioner_details", "respondent_name", "respondent_details"}:
            return {"party_block", "party_detail", "cause_title", "main_body", "header"}
        if field_key.startswith("advocate_"):
            return {"advocate_block", "signature_block", "vakalatnama", "appearance"}
        if field_key in {"crime_no", "crime_year", "police_station"}:
            return {"fir_block", "police_details", "main_body"}
        if field_key in {"subject_category", "provision_of_law", "limitation_dates", "ia_details"}:
            return {"metadata", "scrutiny", "form_field", "main_body"}
        if field_key == "document_index":
            return {"index", "table", "document_list"}
        return {"main_body", "header"}

    def _page_type_matches(self, field_key: str, page_type: str) -> bool:
        mapping = {
            "document_index": {"index_page", "index"},
            "crime_no": {"fir", "police_report", "application_petition"},
            "crime_year": {"fir", "police_report", "application_petition"},
            "police_station": {"fir", "police_report", "application_petition"},
            "petitioner_name": {"hc_cause_title", "party_detail", "main_petition", "memo_of_parties", "application_petition"},
            "petitioner_details": {"hc_cause_title", "party_detail", "main_petition", "memo_of_parties", "application_petition"},
            "respondent_name": {"hc_cause_title", "party_detail", "main_petition", "memo_of_parties", "application_petition"},
            "respondent_details": {"hc_cause_title", "party_detail", "main_petition", "memo_of_parties", "application_petition"},
            "advocate_name": {"memo_of_appearance", "vakalatnama", "advocate"},
            "advocate_enrol_no": {"memo_of_appearance", "vakalatnama", "advocate"},
            "advocate_enrol_year": {"memo_of_appearance", "vakalatnama", "advocate"},
            "lower_court_case_no": {"lower_court_title", "lower_court_order_sheet", "judgment_order"},
            "lower_court_case_year": {"lower_court_title", "lower_court_order_sheet", "judgment_order"},
            "cnr_no": {"lower_court_title", "lower_court_order_sheet", "judgment_order"},
            "judge_name": {"lower_court_order_sheet", "judgment_order"},
            "impugned_order_date": {"lower_court_order_sheet", "judgment_order"},
            "subject_category": {"filing_scrutiny_report", "legal_provision_noise"},
            "provision_of_law": {"filing_scrutiny_report", "legal_provision_noise", "application_petition"},
            "limitation_dates": {"filing_scrutiny_report", "application_petition"},
            "ia_details": {"filing_scrutiny_report", "application_petition"},
            "case_type": {"hc_cause_title", "filing_scrutiny_report", "lower_court_title"},
            "list_type": {"filing_scrutiny_report", "hc_cause_title"},
        }
        return page_type in mapping.get(field_key, set())

    def _save_routes(self, document_id: int, routes: dict[str, Any]) -> None:
        self._route_path(document_id).write_text(
            json.dumps(routes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _route_path(self, document_id: int) -> Path:
        return ROUTING_DIR / f"{document_id}_field_routes.json"

    def _parse_json(self, value: Any) -> Any:
        if not value:
            return []
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return []

    def _normalize(self, value: str) -> str:
        value = (value or "").lower()
        value = value.replace("\u200c", " ").replace("\u200d", " ")
        value = re.sub(r"[^\w\s./:@\-()अ-हािीुूेैोौंंःँ]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _contains(self, normalized_text: str, keyword: str) -> bool:
        return keyword.lower() in normalized_text

    def _excerpt(self, text: str, keywords: list[str], limit: int = 320) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return ""
        low = text.lower()
        positions = [low.find(keyword.lower()) for keyword in keywords if keyword and low.find(keyword.lower()) >= 0]
        if not positions:
            return text[:limit]
        start = max(min(positions) - 90, 0)
        return text[start : start + limit]
