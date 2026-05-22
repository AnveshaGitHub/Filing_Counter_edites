from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.filing.field_page_router_service import FieldPageRouterService

logger = logging.getLogger(__name__)

REGION_DIR = Path("storage/regions")


FIELD_GROUP_TO_REGION = {
    "petitioner_name": "petitioner_details",
    "petitioner_details": "petitioner_details",
    "respondent_name": "respondent_details",
    "respondent_details": "respondent_details",
    "advocate_details": "advocate_details",
    "crime_no": "fir_details",
    "crime_year": "fir_details",
    "police_station": "fir_details",
    "fir_details": "fir_details",
    "lower_court_details": "lower_court_details",
    "impugned_order_details": "lower_court_details",
    "subject_category": "subject_category",
    "provision_of_law": "subject_category",
    "limitation_dates": "limitation_dates",
    "ia_details": "ia_details",
    "document_index": "document_index",
}


REGION_RULES = {
    "petitioner_details": {
        "start": [
            "applicant", "applicants", "appellant", "appellants", "petitioner",
            "petitioners", "plaintiff", "revisionist", "आवेदक", "अपीलार्थी",
            "याचिकाकर्ता", "वादी",
        ],
        "end": [
            "versus", "vs.", "respondent", "respondents", "non-applicant",
            "opposite party", "प्रतिवादी", "अनावेदक", "बनाम", "विरुद्ध",
            "subject heading", "provision of law", "act / section",
        ],
    },
    "respondent_details": {
        "start": [
            "respondent", "respondents", "non-applicant", "opposite party",
            "versus", "vs.", "प्रतिवादी", "अनावेदक", "बनाम", "विरुद्ध",
        ],
        "end": [
            "advocate", "counsel", "learned counsel", "prayer", "subject heading",
            "provision of law", "act / section", "अधिवक्ता", "प्रार्थना",
        ],
    },
    "advocate_details": {
        "start": [
            "advocate", "counsel", "learned counsel", "government advocate",
            "अधिवक्ता", "वकील", "enrol", "enrollment", "enrolment",
        ],
        "end": ["prayer", "verification", "annexure", "index", "subject heading"],
    },
    "fir_details": {
        "start": [
            "crime no", "crime number", "fir no", "fir number", "police station",
            "p.s.", "अपराध क्रमांक", "अपराध क्र", "थाना", "पुलिस थाना",
        ],
        "end": [
            "applicant", "respondent", "prayer", "subject heading",
            "provision of law", "court fee",
        ],
    },
    "lower_court_details": {
        "start": [
            "lower court", "trial court", "district court", "sessions judge",
            "learned court", "impugned judgment", "impugned order", "cnr", "c n r",
            "निचली अदालत", "सत्र न्यायालय",
        ],
        "end": [
            "subject heading", "provision of law", "applicant", "respondent",
            "court fee", "index",
        ],
    },
    "subject_category": {
        "start": [
            "subject heading", "category", "sub-category", "provision of law",
            "act / section", "act/section", "criminal law", "family matters",
            "motor accident",
        ],
        "end": ["court fee", "petitioner", "respondent", "applicant", "advocate"],
    },
    "limitation_dates": {
        "start": [
            "limitation", "date of order", "date of filing", "copying date",
            "delivery ready", "within time", "period of limitation",
        ],
        "end": ["submit", "delete", "lower court", "subject heading"],
    },
    "ia_details": {
        "start": [
            "interlocutory application", "ia no", "i.a.", "extension of time",
            "application no", "annual reg",
        ],
        "end": ["submit", "lower court", "subject heading"],
    },
    "document_index": {
        "start": ["index", "list of documents", "document", "page no", "annexure"],
        "end": ["applicant", "respondent", "subject heading"],
    },
}


NOISE_PATTERNS = [
    r"about\s*:\s*blank",
    r"^\s*page\s+\d+\s*$",
    r"^\s*\d+\s+of\s+\d+\s*$",
    r"firefox",
    r"http[s]?://\S+",
    r"report of cases already filed",
    r"subject heading/category/sub-?category",
    r"desc of the judgment/order/award",
    r"court fee",
    r"fee type",
]


@dataclass
class RegionResult:
    field_group: str
    region_type: str
    page_no: int
    route_score: float
    region_score: float
    start_line: int
    end_line: int
    reasons: list[str]
    text: str
    text_preview: str


class RoutedRegionExtractorService:
    def __init__(self, db: Session):
        self.db = db
        self.router = FieldPageRouterService(db)
        REGION_DIR.mkdir(parents=True, exist_ok=True)

    def build_regions(self, document_id: int) -> dict[str, Any]:
        output: dict[str, Any] = {"document_id": document_id, "regions": {}}
        for field_group in FIELD_GROUP_TO_REGION:
            output["regions"][field_group] = [
                asdict(result) for result in self.extract_regions(document_id, field_group)
            ]

        self._region_path(document_id).write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output

    def get_regions(self, document_id: int) -> dict[str, Any]:
        path = self._region_path(document_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("[ROUTED REGION] failed to read cached regions")
        return self.build_regions(document_id)

    def get_region_for_group(self, document_id: int, field_group: str) -> dict[str, Any]:
        all_regions = self.get_regions(document_id)
        return {
            "document_id": document_id,
            "field_group": field_group,
            "regions": all_regions.get("regions", {}).get(field_group, []),
        }

    def get_context(self, document_id: int, field_group: str, max_chars: int = 5000) -> str:
        regions = self.extract_regions(document_id, field_group)
        if not regions:
            return self.router.get_context(document_id, field_group, max_chars=max_chars)

        chunks = []
        for region in regions[:3]:
            if region.text.strip():
                chunks.append(
                    f"\n--- REGION {region.region_type} | PAGE {region.page_no} | score={region.region_score} ---\n{region.text}"
                )
        text = "\n".join(chunks).strip()
        return text[:max_chars]

    def get_region_pages(self, document_id: int, field_group: str, max_regions: int = 5) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        for region in self.extract_regions(document_id, field_group)[:max_regions]:
            if not region.text.strip():
                continue
            pages.append(
                {
                    "page_no": region.page_no,
                    "text": region.text,
                    "ocr_confidence": None,
                    "page_types": [region.region_type],
                    "layout_signals": region.reasons,
                    "route_score": region.route_score,
                    "region_score": region.region_score,
                    "region_type": region.region_type,
                    "route_reasons": region.reasons,
                }
            )
        return pages

    def extract_regions(self, document_id: int, field_group: str) -> list[RegionResult]:
        region_type = FIELD_GROUP_TO_REGION.get(field_group, field_group)
        rules = REGION_RULES.get(region_type)
        routed = self.router.get_route_for_group(document_id, field_group)
        selected_pages = routed.get("selected_pages", [])

        if not rules or not selected_pages:
            return self._fallback_region(document_id, field_group, region_type, "fallback:routed_context")

        results: list[RegionResult] = []
        page_text_map = self._load_routed_page_texts(document_id, selected_pages)

        for page_item in selected_pages:
            page_no = int(page_item.get("page_no") or 0)
            route_score = float(page_item.get("score") or 0.0)
            text = page_text_map.get(page_no, "")
            if not text.strip():
                continue

            results.extend(
                self._extract_from_lines(
                    field_group=field_group,
                    region_type=region_type,
                    page_no=page_no,
                    route_score=route_score,
                    lines=self._to_lines(text),
                    rules=rules,
                )
            )

        results.sort(key=lambda item: (item.region_score, item.route_score), reverse=True)
        if not results:
            return self._fallback_region(document_id, field_group, region_type, "fallback:no_anchor_region")
        return results[:5]

    def _extract_from_lines(
        self,
        field_group: str,
        region_type: str,
        page_no: int,
        route_score: float,
        lines: list[str],
        rules: dict[str, list[str]],
    ) -> list[RegionResult]:
        norm_lines = [self._normalize(line) for line in lines]
        starts = self._find_anchor_lines(norm_lines, rules["start"])
        ends = self._find_anchor_lines(norm_lines, rules["end"])
        regions: list[RegionResult] = []

        if not starts and region_type in {"petitioner_details", "respondent_details"}:
            starts = self._find_party_like_lines(norm_lines)

        for start_idx in starts[:4]:
            end_idx = self._find_next_end(start_idx, ends, len(lines), region_type)
            cleaned_text = self._clean_region_text("\n".join(lines[start_idx:end_idx]), region_type)
            if len(cleaned_text) < 8:
                continue

            region_score, reasons = self._score_region(region_type, cleaned_text)
            if region_score <= 0:
                continue

            regions.append(
                RegionResult(
                    field_group=field_group,
                    region_type=region_type,
                    page_no=page_no,
                    route_score=route_score,
                    region_score=round(region_score, 4),
                    start_line=start_idx + 1,
                    end_line=end_idx,
                    reasons=reasons,
                    text=cleaned_text,
                    text_preview=self._preview(cleaned_text),
                )
            )
        return regions

    def _fallback_region(
        self,
        document_id: int,
        field_group: str,
        region_type: str,
        reason: str,
    ) -> list[RegionResult]:
        fallback = self.router.get_context(document_id, field_group)
        if not fallback:
            return []
        cleaned = self._clean_region_text(fallback, region_type)
        return [
            RegionResult(
                field_group=field_group,
                region_type=region_type,
                page_no=0,
                route_score=0.0,
                region_score=0.2,
                start_line=0,
                end_line=0,
                reasons=[reason],
                text=cleaned,
                text_preview=self._preview(cleaned),
            )
        ]

    def _load_routed_page_texts(self, document_id: int, selected_pages: list[dict[str, Any]]) -> dict[int, str]:
        page_map = {page["page_no"]: page for page in self.router._load_pages(document_id)}
        out: dict[int, str] = {}
        for item in selected_pages:
            page_no = int(item.get("page_no") or 0)
            page = page_map.get(page_no)
            if page:
                out[page_no] = page.get("clean_text") or page.get("ocr_text") or ""
        return out

    def _to_lines(self, text: str) -> list[str]:
        lines = []
        for line in re.split(r"[\r\n]+", text or ""):
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                lines.append(line)
        return lines

    def _find_anchor_lines(self, norm_lines: list[str], anchors: list[str]) -> list[int]:
        indexes = []
        for idx, line in enumerate(norm_lines):
            if any(anchor.lower() in line for anchor in anchors):
                indexes.append(idx)
        return indexes

    def _find_party_like_lines(self, norm_lines: list[str]) -> list[int]:
        pattern = re.compile(
            r"\b(s/o|w/o|d/o|aged|age|occupation|r/o|resident|district|tehsil|village)\b"
            r"|पिता|पत्नी|उम्र|निवासी|ग्राम|तहसील|जिला"
        )
        indexes = []
        for idx, line in enumerate(norm_lines):
            if pattern.search(line):
                indexes.append(max(idx - 2, 0))
        return indexes[:3]

    def _find_next_end(self, start_idx: int, end_indexes: list[int], total_lines: int, region_type: str) -> int:
        for end in end_indexes:
            if end > start_idx + 1:
                return min(end, start_idx + self._max_region_lines(region_type))
        return min(total_lines, start_idx + self._max_region_lines(region_type))

    def _max_region_lines(self, region_type: str) -> int:
        if region_type in {"petitioner_details", "respondent_details"}:
            return 22
        if region_type in {"advocate_details", "fir_details"}:
            return 18
        if region_type == "lower_court_details":
            return 25
        if region_type == "document_index":
            return 35
        return 20

    def _score_region(self, region_type: str, text: str) -> tuple[float, list[str]]:
        norm = self._normalize(text)
        score = 0.0
        reasons: list[str] = []

        if region_type in {"petitioner_details", "respondent_details"}:
            if re.search(r"\b(s/o|w/o|d/o)\b|पिता|पत्नी", norm):
                score += 0.25
                reasons.append("relation_found")
            if re.search(r"\baged?\b|उम्र|वर्ष", norm):
                score += 0.18
                reasons.append("age_found")
            if re.search(r"\br/o\b|resident|निवासी|ग्राम|जिला|district", norm):
                score += 0.25
                reasons.append("address_found")
            if re.search(r"applicant|appellant|petitioner|respondent|versus|बनाम|प्रतिवादी|आवेदक", norm):
                score += 0.20
                reasons.append("party_anchor_found")
        elif region_type == "fir_details":
            if re.search(r"crime\s*no|fir\s*no|अपराध", norm):
                score += 0.35
                reasons.append("crime_no_found")
            if re.search(r"police\s*station|p\.s\.|थाना", norm):
                score += 0.30
                reasons.append("police_station_found")
            if re.search(r"section|u/s|धारा", norm):
                score += 0.20
                reasons.append("section_found")
        elif region_type == "lower_court_details":
            if re.search(r"cnr|case\s*no|district|sessions|judge|court", norm):
                score += 0.35
                reasons.append("court_terms_found")
            if re.search(r"impugned|judgment|order|award|निर्णय|आदेश", norm):
                score += 0.30
                reasons.append("impugned_terms_found")
        elif region_type == "advocate_details":
            if re.search(r"advocate|counsel|अधिवक्ता|वकील", norm):
                score += 0.35
                reasons.append("advocate_anchor_found")
            if re.search(r"enrol|mobile|email|@|\b\d{10}\b", norm):
                score += 0.25
                reasons.append("contact_or_enrol_found")
        elif region_type == "subject_category":
            if re.search(r"subject|category|sub-category|provision|act|section", norm):
                score += 0.45
                reasons.append("subject_category_found")
        elif region_type == "document_index":
            if re.search(r"index|list of documents|page no|annexure", norm):
                score += 0.45
                reasons.append("index_found")
        else:
            score += 0.2
            reasons.append("generic_region")

        noise_hits = sum(1 for pattern in NOISE_PATTERNS if re.search(pattern, norm, flags=re.I))
        if noise_hits:
            score -= min(0.25, noise_hits * 0.06)
            reasons.append(f"noise_penalty:{noise_hits}")

        token_count = len(norm.split())
        if token_count > 180:
            score -= 0.15
            reasons.append("too_long_penalty")
        elif token_count < 3:
            score -= 0.2
            reasons.append("too_short_penalty")
        return max(score, 0.0), reasons

    def _clean_region_text(self, text: str, region_type: str) -> str:
        cleaned_lines = []
        for line in self._to_lines(text):
            normalized = self._normalize(line)
            if self._is_noise_line(normalized, region_type):
                continue
            line = re.sub(r"\s+", " ", line).strip()
            line = re.sub(r"^[\|\-_:;,. ]+", "", line)
            line = re.sub(r"[\|\-_:;,. ]+$", "", line)
            if line:
                cleaned_lines.append(line)

        deduped = []
        prev = None
        for line in cleaned_lines:
            key = self._normalize(line)
            if key and key != prev:
                deduped.append(line)
            prev = key
        return "\n".join(deduped).strip()

    def _is_noise_line(self, normalized: str, region_type: str) -> bool:
        patterns = list(NOISE_PATTERNS)
        if region_type == "subject_category":
            patterns = [
                pattern
                for pattern in patterns
                if pattern not in {r"provision of law\s*:", r"act\s*/\s*section\s*:"}
            ]
        return any(re.search(pattern, normalized, flags=re.I) for pattern in patterns)

    def _normalize(self, text: str) -> str:
        text = (text or "").lower()
        text = text.replace("\u200c", " ").replace("\u200d", " ")
        text = re.sub(r"[^\w\s./:@\-()अ-हािीुूेैोौंंःँ]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _preview(self, text: str, limit: int = 260) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text[:limit]

    def _region_path(self, document_id: int) -> Path:
        return REGION_DIR / f"{document_id}_regions.json"
