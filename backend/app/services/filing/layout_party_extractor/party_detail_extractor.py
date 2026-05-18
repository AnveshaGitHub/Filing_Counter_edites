from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.services.filing.field_quality_gate_service import FieldQualityGateService
from app.services.filing.layout_party_extractor.bilingual_legal_labels import (
    ADDRESS_LABELS,
    DISTRICT_LABELS,
    OCCUPATION_LABELS,
    STATE_LABELS,
    TEHSIL_LABELS,
    VILLAGE_LABELS,
)
from app.services.filing.layout_party_extractor.layout_line_builder import LayoutLineBuilder
from app.services.filing.layout_party_extractor.layout_models import PartyBlock, PartyDetail
from app.services.filing.layout_party_extractor.ocr_text_party_block_parser import OCRTextPartyBlockParser
from app.services.filing.layout_party_extractor.party_block_parser import PartyBlockParser
from app.services.filing.page_classifier_service import PageClassifierService

logger = logging.getLogger(__name__)


class LayoutAwarePartyDetailExtractor:
    ALLOWED_PAGE_TYPES = {"hc_cause_title", "application_petition", "lower_court_title"}
    LOCATION_KEYS = {"district", "tehsil", "village"}

    def __init__(self, db: Session) -> None:
        self.db = db
        self.quality_gate = FieldQualityGateService()
        self.line_builder = LayoutLineBuilder(db)
        self.block_parser = PartyBlockParser()
        self.ocr_text_block_parser = OCRTextPartyBlockParser()
        self.classifier = PageClassifierService(db)

    def extract(self, document_id: int) -> list[FieldSpecificCandidate]:
        classification = self.classifier.classify_document_from_db(document_id)
        allowed_pages = {
            page.page_no
            for page in classification.pages
            if page.page_type in self.ALLOWED_PAGE_TYPES
        }

        if not allowed_pages:
            allowed_pages = {page.page_no for page in classification.pages if page.page_no <= 5}

        page_text_pairs = self._load_allowed_page_texts(document_id, allowed_pages)
        ocr_text_candidates = self.ocr_text_block_parser.extract_candidates_from_pages(page_text_pairs)

        lines = self.line_builder.load_lines(document_id, allowed_page_nos=allowed_pages)
        blocks = self.block_parser.parse(lines)

        candidates: list[FieldSpecificCandidate] = []
        for block in blocks:
            for detail in self._extract_details_from_block(block):
                candidate = self._to_candidate(detail)
                if candidate:
                    candidates.append(candidate)

        candidates.extend(ocr_text_candidates)

        logger.info(
            "[LAYOUT PARTY] document_id=%s, candidates=%s, pages_used=%s",
            document_id,
            len(candidates),
            sorted(allowed_pages),
        )

        return self._dedupe(candidates)

    def _load_allowed_page_texts(self, document_id: int, allowed_pages: set[int]) -> list[tuple[int, str]]:
        rows = []

        try:
            from app.models.local_test_document_page import LocalTestDocumentPage

            rows = (
                self.db.query(LocalTestDocumentPage)
                .filter(LocalTestDocumentPage.document_id == document_id)
                .order_by(LocalTestDocumentPage.page_no.asc())
                .all()
            )
        except Exception:
            rows = []

        out: list[tuple[int, str]] = []
        for row in rows:
            page_no = int(getattr(row, "page_no", 0) or 0)
            if allowed_pages and page_no not in allowed_pages:
                continue

            text = getattr(row, "ocr_text", None) or getattr(row, "text", None) or ""
            if text:
                out.append((page_no, text))

        return out

    def _extract_details_from_block(self, block: PartyBlock) -> list[PartyDetail]:
        text = self._clean(" ".join(line.text for line in block.lines))
        side_prefix = "petitioner" if block.side == "petitioner" else "respondent"
        evidence = text[:240]
        details: list[PartyDetail] = []

        name = self._extract_name(block, text)
        if name:
            details.append(
                PartyDetail(
                    field_key=f"{side_prefix}_name",
                    value=name,
                    confidence=min(0.9, block.confidence + 0.05),
                    page_no=block.page_no,
                    evidence=evidence,
                )
            )

        relation, related_name = self._extract_relation_and_name(text)
        if relation:
            details.append(
                PartyDetail(
                    field_key=f"{side_prefix}_relation",
                    value=relation,
                    confidence=0.83,
                    page_no=block.page_no,
                    evidence=evidence,
                )
            )
        if related_name:
            details.append(
                PartyDetail(
                    field_key=f"{side_prefix}_father_or_husband",
                    value=related_name,
                    confidence=0.82,
                    page_no=block.page_no,
                    evidence=evidence,
                )
            )

        self._append_detail(details, side_prefix, "age", self._extract_age(text), 0.84, block.page_no, evidence)
        self._append_detail(
            details,
            side_prefix,
            "occupation",
            self._extract_labeled_value(
                text,
                OCCUPATION_LABELS,
                stop_labels=["R/o", "resident", "निवासी", "district", "जिला"],
            ),
            0.76,
            block.page_no,
            evidence,
        )
        self._append_detail(details, side_prefix, "address", self._extract_address(text), 0.74, block.page_no, evidence)
        self._append_detail(
            details,
            side_prefix,
            "district",
            self._extract_labeled_value(
                text,
                DISTRICT_LABELS,
                stop_labels=["tehsil", "तहसील", "village", "ग्राम", "p.s.", "police"],
            ),
            0.78,
            block.page_no,
            evidence,
        )
        self._append_detail(
            details,
            side_prefix,
            "tehsil",
            self._extract_labeled_value(text, TEHSIL_LABELS, stop_labels=["district", "जिला", "village", "ग्राम"]),
            0.73,
            block.page_no,
            evidence,
        )
        self._append_detail(
            details,
            side_prefix,
            "village",
            self._extract_labeled_value(text, VILLAGE_LABELS, stop_labels=["district", "जिला", "tehsil", "तहसील", "p.s."]),
            0.73,
            block.page_no,
            evidence,
        )
        self._append_detail(details, side_prefix, "state", self._extract_state(text), 0.72, block.page_no, evidence)

        return details

    def _append_detail(
        self,
        details: list[PartyDetail],
        side_prefix: str,
        key: str,
        value: str | None,
        confidence: float,
        page_no: int,
        evidence: str,
    ) -> None:
        if not value:
            return
        details.append(
            PartyDetail(
                field_key=f"{side_prefix}_{key}",
                value=value,
                confidence=confidence,
                page_no=page_no,
                evidence=evidence,
            )
        )

    def _extract_name(self, block: PartyBlock, text: str) -> str | None:
        text2 = text
        if block.label not in {"VERSUS_BEFORE", "VERSUS_AFTER"}:
            text2 = re.sub(rf"\b{re.escape(block.label)}\b\s*[:\-]?", " ", text2, flags=re.I)
        text2 = re.sub(
            r"\b(APPLICANT|RESPONDENT|NON-APPLICANT|NON APPLICANT|APPELLANT|PETITIONER|PLAINTIFF|DEFENDANT|CLAIMANT)\b\s*[:\-]?",
            " ",
            text2,
            flags=re.I,
        )
        text2 = re.sub(r"\b(आवेदक|अनावेदक|प्रतिवादी|अपीलार्थी|याचिकाकर्ता|वादी)\b\s*[:\-]?", " ", text2)

        name_part = re.split(
            r"\b(S/o|W/o|D/o|son of|wife of|daughter of|Age|Aged|Occupation|R/o|resident|पुत्र|पत्नी|पुत्री|आयु|उम्र|निवासी|व्यवसाय)\b",
            text2,
            maxsplit=1,
            flags=re.I,
        )[0]

        return self._clean_person_name(name_part)

    def _extract_relation_and_name(self, text: str) -> tuple[str | None, str | None]:
        patterns = [
            (r"\b(S/o|S\/O)\s+([^,।]+)", "S/o"),
            (r"\b(W/o|W\/O)\s+([^,।]+)", "W/o"),
            (r"\b(D/o|D\/O)\s+([^,।]+)", "D/o"),
            (r"\bson of\s+([^,।]+)", "S/o"),
            (r"\bwife of\s+([^,।]+)", "W/o"),
            (r"\bdaughter of\s+([^,।]+)", "D/o"),
            (r"पुत्र\s+([^,।]+)", "S/o"),
            (r"पत्नी\s+([^,।]+)", "W/o"),
            (r"पुत्री\s+([^,।]+)", "D/o"),
            (r"पिता\s+([^,।]+)", "S/o"),
        ]

        for pattern, relation in patterns:
            match = re.search(pattern, text, flags=re.I)
            if not match:
                continue
            name = match.group(2) if len(match.groups()) >= 2 else match.group(1)
            return relation, self._clean_person_name(name)

        return None, None

    def _extract_age(self, text: str) -> str | None:
        patterns = [
            r"\bAge\s*[-:]?\s*(\d{1,3})\s*(?:years|yrs)?\b",
            r"\bAged\s*(?:about)?\s*(\d{1,3})\s*(?:years|yrs)?\b",
            r"आयु\s*[-:]?\s*(\d{1,3})",
            r"उम्र\s*[-:]?\s*(\d{1,3})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                age = int(match.group(1))
                if 0 < age < 120:
                    return str(age)
        return None

    def _extract_address(self, text: str) -> str | None:
        for label in ADDRESS_LABELS:
            match = re.search(rf"{re.escape(label)}\s*[-:]?\s*(.+)", text, flags=re.I)
            if not match:
                continue
            value = re.split(
                r"\b(Age|Aged|Occupation|व्यवसाय|आयु|उम्र)\b",
                match.group(1),
                maxsplit=1,
                flags=re.I,
            )[0]
            value = self._clean_address(value)
            if value:
                return value
        return None

    def _extract_labeled_value(self, text: str, labels: list[str], stop_labels: list[str]) -> str | None:
        for label in labels:
            match = re.search(
                rf"{re.escape(label)}\s*[-:]?\s*([^,।]+(?:\s+[A-Za-z\u0900-\u097F.]+){{0,4}})",
                text,
                flags=re.I,
            )
            if not match:
                continue

            value = match.group(1)
            for stop in stop_labels:
                value = re.split(re.escape(stop), value, maxsplit=1, flags=re.I)[0]

            value = self._clean_short_value(value)
            if value:
                return value
        return None

    def _extract_state(self, text: str) -> str | None:
        low = text.lower()
        for label in STATE_LABELS:
            if label.lower() in low:
                return label
        return None

    def _to_candidate(self, detail: PartyDetail) -> FieldSpecificCandidate | None:
        quality_key = self._quality_key(detail.field_key)
        quality = self.quality_gate.validate(quality_key, detail.value)
        value = detail.value
        validation_note = None
        confidence = detail.confidence

        if quality.status == "rejected":
            if quality_key in self.LOCATION_KEYS and quality.reason and quality.reason.startswith("unknown_"):
                validation_note = quality.reason
                confidence = min(confidence, 0.73)
            else:
                return None
        elif quality.cleaned_value:
            value = quality.cleaned_value

        return FieldSpecificCandidate(
            field_key=detail.field_key,
            value=value,
            normalized_value=value,
            confidence=confidence,
            page_no=detail.page_no,
            page_type="layout_party_block",
            evidence=detail.evidence,
            extractor="phase_9_4_layout_bilingual_party_extractor",
            status="confirmed" if confidence >= 0.88 else "suggested",
            validation_note=validation_note,
        )

    def _quality_key(self, field_key: str) -> str:
        for prefix in ["petitioner_", "respondent_"]:
            if field_key.startswith(prefix):
                suffix = field_key.replace(prefix, "", 1)
                if suffix == "name":
                    return field_key
                return suffix
        return field_key

    def _dedupe(self, candidates: list[FieldSpecificCandidate]) -> list[FieldSpecificCandidate]:
        best: dict[tuple[str, str], FieldSpecificCandidate] = {}
        for cand in candidates:
            key = (cand.field_key, (cand.normalized_value or cand.value).upper())
            old = best.get(key)
            if old is None or cand.confidence > old.confidence:
                best[key] = cand
        return sorted(best.values(), key=lambda c: c.confidence, reverse=True)

    def _clean(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.replace("about:blank", " ")
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _clean_person_name(self, value: str | None) -> str | None:
        if not value:
            return None

        value = self._clean(value)
        value = re.sub(r"\[[A-Z0-9\-]+\]", " ", value)
        value = re.sub(r"^(Smt\.?|Shri|Sri|Mr\.?|Mrs\.?|Ms\.?)\s+", "", value, flags=re.I)
        value = re.sub(r"[^A-Za-z\u0900-\u097F .]", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" .,-:")
        value = re.sub(
            r"^(IN THE HIGH COURT|PRINCIPAL SEAT|APPLICANT|RESPONDENT)\b.*",
            "",
            value,
            flags=re.I,
        ).strip()

        if len(value) < 2 or len(value) > 80:
            return None

        return value

    def _clean_address(self, value: str | None) -> str | None:
        if not value:
            return None
        value = self._clean(value)
        value = re.split(
            r"\b(District|Distt|Tehsil|Village|जिला|तहसील|ग्राम)\b",
            value,
            maxsplit=1,
            flags=re.I,
        )[0]
        value = re.split(r"\b(versus|respondent|appellant|applicant)\b", value, maxsplit=1, flags=re.I)[0]
        value = value.strip(" ,.-")
        if len(value) < 3 or len(value) > 180:
            return None
        return value

    def _clean_short_value(self, value: str | None) -> str | None:
        if not value:
            return None
        value = self._clean(value)
        value = re.sub(r"[^A-Za-z\u0900-\u097F .-]", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" .,-:")
        if len(value) < 2 or len(value) > 60:
            return None
        return value
