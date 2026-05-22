from __future__ import annotations

import re
from sqlalchemy.orm import Session

from app.models.extracted_field import ExtractedField
from app.models.local_test_document_page import LocalTestDocumentPage
from app.services.filing.field_quality_gate_service import FieldQualityGateService
from app.services.filing.document_type_router_service import DocumentTypeRouterService
from app.services.filing.filing_metadata_graph_extractor import FilingMetadataGraphExtractor
from app.services.filing.layout_party_extractor.ocr_text_party_block_parser import OCRTextPartyBlockParser
from app.services.filing.page_priority_service import PageText
from app.schemas.party_autofill import PartyAutofillResponse, PartyAutofillData, PartyAutofillField


class StrictPartyAutofillService:
    RELATION_RE = re.compile(r"\b(S/O|D/O|W/O|C/O)\b\.?\s*([A-Za-z .]{2,80})", re.I)
    OCCUPATION_RE = re.compile(r"\bOccupation\b\s*[:\-]?\s*([A-Za-z ]{3,60})", re.I)
    DOB_RE = re.compile(r"\b(?:DOB|Date of Birth)\b\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.I)
    AGE_RE = re.compile(r"\b(?:Aged?|Age)\b\s*(?:about)?\s*[:\-]?\s*(\d{1,3})\b", re.I)
    MOBILE_RE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
    EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
    PIN_RE = re.compile(r"\b(\d{6})\b")
    DISTRICT_RE = re.compile(r"\bDistrict\b\s*[:\-]?\s*([A-Za-z .]{2,60})", re.I)
    TEHSIL_RE = re.compile(r"\bTehsil\b\s*[:\-]?\s*([A-Za-z .]{2,60})", re.I)
    VILLAGE_RE = re.compile(r"\bVillage\b\s*[:\-]?\s*([A-Za-z .]{2,60})", re.I)
    STATE_RE = re.compile(r"\bState\b\s*[:\-]?\s*([A-Za-z .]{2,60})", re.I)
    ADDRESS_RE = re.compile(r"\b(?:R/o|Address)\b\s*[:\-]?\s*([^\n]{8,180})", re.I)
    GENDER_RE = re.compile(r"\b(Male|Female|Other)\b", re.I)
    COUNTRY_RE = re.compile(r"\b(India)\b", re.I)
    CASTE_RE = re.compile(r"\b(?:Caste|Category)\b\s*[:\-]?\s*([A-Za-z\- ]{2,60})", re.I)
    IDENTITY_RE = re.compile(r"\b(?:Identity Proof|ID Proof)\b\s*[:\-]?\s*([A-Za-z0-9 \-]{2,60})", re.I)

    def __init__(self, db: Session) -> None:
        self.db = db
        self.quality_gate = FieldQualityGateService()
        self.ocr_text_block_parser = OCRTextPartyBlockParser()
        self.graph_extractor = FilingMetadataGraphExtractor(db)

    def _clean(self, text: str | None) -> str:
        if not text:
            return ""
        value = text.replace("about:blank", " ")
        value = re.sub(r"\s{2,}", " ", value)
        return value.strip()

    def _pages_text(self, document_id: int) -> list[tuple[int, str]]:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        return [(row.page_no, self._clean(row.ocr_text)) for row in rows if row.ocr_text]

    def is_lower_court_source(self, document_id: int) -> bool:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .limit(30)
            .all()
        )
        pages = [
            PageText(
                page_no=row.page_no,
                text=row.ocr_text or "",
                page_type=getattr(row, "page_type", None) or getattr(row, "detected_page_type", None),
            )
            for row in rows
        ]
        decision = DocumentTypeRouterService().decide(pages)
        return decision.document_type in {"lower_court_record", "order_sheet_bundle"}

    def _party_window(self, text: str, side: str) -> str:
        patterns = {
            "petitioner": [r"\bAPPLICANT\b", r"\bPETITIONER\b", r"\bAPPELLANT\b"],
            "respondent": [r"\bRESPONDENT\b", r"\bNON-APPLICANT\b", r"\bVERSUS\b", r"\bSTATE OF\b"],
        }
        for pat in patterns[side]:
            match = re.search(pat, text, re.I)
            if match:
                return text[match.start(): match.start() + 900]
        return text[:900]

    def _pick_unique(self, pattern: re.Pattern, windows: list[tuple[int, str]]) -> tuple[PartyAutofillField, bool]:
        matches: list[tuple[int, str, str]] = []
        for page_no, text in windows:
            for match in pattern.finditer(text):
                matches.append((page_no, match.group(0), match.group(1) if match.lastindex else match.group(0)))

        cleaned: list[tuple[int, str, str]] = []
        for page_no, evidence, value in matches:
            val = self._clean(value)
            if val:
                cleaned.append((page_no, evidence, val))

        unique_values = list({item[2] for item in cleaned})
        if len(unique_values) != 1:
            return PartyAutofillField(), True

        page_no, evidence, value = cleaned[0]
        return (
            PartyAutofillField(
                value=value,
                confidence=0.98,
                source_page=page_no,
                evidence=evidence[:160],
            ),
            False,
        )

    def _apply_parser_candidates(
        self,
        document_id: int,
        side: str,
        page_texts: list[tuple[int, str]],
        lower_court_source: bool,
    ) -> PartyAutofillResponse | None:
        candidates = self.ocr_text_block_parser.extract_candidates_from_pages(page_texts)
        prefix = f"{side}_"
        field_names = {
            "relation",
            "father_or_husband",
            "occupation",
            "age",
            "district",
            "tehsil",
            "village",
            "state",
            "address",
        }

        side_candidates = [
            candidate
            for candidate in candidates
            if candidate.field_key.startswith(prefix) and candidate.status != "rejected"
        ]
        if not side_candidates:
            return None

        current_name = self._current_party_name(document_id, side)
        selected_key = self._select_parser_block_key(side_candidates, prefix, current_name)
        if not selected_key:
            return None

        best_by_field = {}
        for candidate in side_candidates:
            block_key = (candidate.page_no, candidate.evidence or "")
            if block_key != selected_key:
                continue
            field_name = candidate.field_key.replace(prefix, "", 1)
            if field_name not in field_names:
                continue

            old = best_by_field.get(field_name)
            if old is None or candidate.confidence > old.confidence:
                best_by_field[field_name] = candidate

        if not best_by_field:
            return None

        data = PartyAutofillData()
        accepted: list[str] = []
        skipped: list[str] = ["name_suffix"]
        quality_results = []

        for field_name, candidate in best_by_field.items():
            quality = self.quality_gate.validate(field_name, candidate.value)
            quality_results.append(quality)
            if quality.status not in {"accepted", "cleaned"}:
                skipped.append(f"{field_name}:{quality.reason or 'quality_rejected'}")
                continue

            value = quality.cleaned_value or candidate.value
            setattr(
                data,
                field_name,
                PartyAutofillField(
                    value=value,
                    confidence=candidate.confidence,
                    source_page=candidate.page_no,
                    evidence=candidate.evidence,
                ),
            )
            accepted.append(field_name)

        if not accepted:
            return None

        if lower_court_source:
            skipped.append("lower_court_source_review_warning_parser_candidates_applied")

        return PartyAutofillResponse(
            document_id=document_id,
            side=side,
            safe_to_apply=True,
            data=data,
            accepted_fields=sorted(set(accepted)),
            rejected_fields=[],
            skipped_fields=sorted(set(skipped)),
            quality_results=quality_results,
        )

    def _current_party_name(self, document_id: int, side: str) -> str | None:
        field_key = f"{side}_name"
        row = (
            self.db.query(ExtractedField)
            .filter(ExtractedField.document_id == document_id)
            .filter(ExtractedField.field_key == field_key)
            .order_by(ExtractedField.id.desc())
            .first()
        )
        if not row:
            return None
        if row.status != "confirmed" and float(row.confidence or 0.0) < 0.85:
            return None
        return self._clean(row.normalized_value or row.raw_value)

    def _select_parser_block_key(self, candidates: list, prefix: str, current_name: str | None) -> tuple[int | None, str] | None:
        grouped: dict[tuple[int | None, str], list] = {}
        for candidate in candidates:
            grouped.setdefault((candidate.page_no, candidate.evidence or ""), []).append(candidate)

        if current_name:
            current_tokens = self._name_tokens(current_name)
            best_match = None
            best_score = 0
            for key, group in grouped.items():
                name_candidates = [c for c in group if c.field_key == f"{prefix}name"]
                for candidate in name_candidates:
                    score = len(current_tokens & self._name_tokens(candidate.value))
                    if score > best_score:
                        best_match = key
                        best_score = score
            if best_match and best_score >= 2:
                return best_match

        scored = sorted(
            grouped.items(),
            key=lambda item: (
                sum(1 for c in item[1] if c.field_key != f"{prefix}name"),
                max((c.confidence for c in item[1]), default=0.0),
            ),
            reverse=True,
        )
        return scored[0][0] if scored else None

    def _name_tokens(self, value: str | None) -> set[str]:
        if not value:
            return set()
        return {token for token in re.findall(r"[A-Za-z]{2,}", value.upper()) if token not in {"THE", "STATE"}}

    def autofill(self, document_id: int, side: str) -> PartyAutofillResponse:
        page_texts = self._pages_text(document_id)
        lower_court_source = self.is_lower_court_source(document_id)

        graph_response = self._autofill_from_party_graph(document_id, side, lower_court_source)
        if graph_response:
            return graph_response

        parser_response = self._apply_parser_candidates(
            document_id=document_id,
            side=side,
            page_texts=page_texts,
            lower_court_source=lower_court_source,
        )
        if parser_response:
            return parser_response

        if lower_court_source:
            return PartyAutofillResponse(
                document_id=document_id,
                side=side,
                safe_to_apply=False,
                data=PartyAutofillData(),
                accepted_fields=[],
                rejected_fields=[],
                skipped_fields=["lower_court_source_requires_operator_review"],
                quality_results=[],
            )

        windows = [(page_no, self._party_window(text, side)) for page_no, text in page_texts]

        data = PartyAutofillData()
        accepted: list[str] = []
        rejected: list[str] = []
        skipped: list[str] = []
        quality_results = []

        field_map = {
            "relation": self.RELATION_RE,
            "occupation": self.OCCUPATION_RE,
            "date_of_birth": self.DOB_RE,
            "age": self.AGE_RE,
            "phone_mobile": self.MOBILE_RE,
            "email_id": self.EMAIL_RE,
            "pincode": self.PIN_RE,
            "district": self.DISTRICT_RE,
            "tehsil": self.TEHSIL_RE,
            "village": self.VILLAGE_RE,
            "state": self.STATE_RE,
            "address": self.ADDRESS_RE,
            "gender": self.GENDER_RE,
            "country": self.COUNTRY_RE,
            "caste": self.CASTE_RE,
            "identity_proof": self.IDENTITY_RE,
        }

        for field_name, pattern in field_map.items():
            field_value, was_skipped = self._pick_unique(pattern, windows)
            if not field_value.value:
                setattr(data, field_name, PartyAutofillField())
                if field_name != "country":
                    skipped.append(field_name)
                continue

            quality = self.quality_gate.validate(field_name, field_value.value)
            quality_results.append(quality)

            if field_name == "gender" and str(field_value.value or "").strip().lower() == "other":
                setattr(data, field_name, PartyAutofillField())
                skipped.append("gender:unsafe_default_other")
                continue

            if quality.status in {"accepted", "cleaned"} and quality.cleaned_value:
                field_value.value = quality.cleaned_value
                # Slightly reduce confidence when value required cleanup.
                if quality.status == "cleaned":
                    base = field_value.confidence or 0.98
                    field_value.confidence = max(0.0, base - quality.confidence_penalty)
                setattr(data, field_name, field_value)
                accepted.append(field_name)
            elif quality.status == "skipped" or was_skipped:
                setattr(data, field_name, PartyAutofillField())
                if not (field_name == "country" and quality.reason == "empty"):
                    skipped.append(field_name if not quality.reason else f"{field_name}:{quality.reason}")
            else:
                setattr(data, field_name, PartyAutofillField())
                if not (field_name == "country" and quality.reason == "empty"):
                    rejected.append(f"{field_name}:{quality.reason or 'quality_rejected'}")

        relation_field = data.relation
        if relation_field.value:
            relation_match = None
            source_page: int | None = relation_field.source_page
            for page_no, text in windows:
                relation_match = self.RELATION_RE.search(text)
                if relation_match:
                    source_page = page_no
                    break
            if relation_match:
                raw_fh = self._clean(relation_match.group(2))
                quality = self.quality_gate.validate("father_or_husband", raw_fh)
                quality_results.append(quality)
                if quality.status in {"accepted", "cleaned"} and quality.cleaned_value:
                    data.father_or_husband = PartyAutofillField(
                        value=quality.cleaned_value,
                        confidence=max(0.0, 0.98 - quality.confidence_penalty),
                        source_page=source_page,
                        evidence=relation_match.group(0)[:160],
                    )
                    accepted.append("father_or_husband")
                elif quality.status == "skipped":
                    skipped.append("father_or_husband")
                else:
                    rejected.append(f"father_or_husband:{quality.reason or 'quality_rejected'}")
            else:
                skipped.append("father_or_husband")
        else:
            skipped.append("father_or_husband")

        skipped.append("name_suffix")

        return PartyAutofillResponse(
            document_id=document_id,
            side=side,
            safe_to_apply=True,
            data=data,
            accepted_fields=sorted(set(accepted)),
            rejected_fields=sorted(set(rejected)),
            skipped_fields=sorted(set(skipped)),
            quality_results=quality_results,
        )

    def _autofill_from_party_graph(
        self,
        document_id: int,
        side: str,
        lower_court_source: bool,
    ) -> PartyAutofillResponse | None:
        party = self.graph_extractor.main_party(document_id, side)
        if not party:
            return None

        field_values = {
            "relation": party.relation,
            "father_or_husband": party.father_husband_name,
            "age": party.age,
            "occupation": party.occupation,
            "state": party.state,
            "district": party.district,
            "tehsil": party.tehsil,
            "village": party.place_city,
            "phone_mobile": party.phone_mobile,
            "email_id": party.email_id,
            "address": party.present_address or party.address,
        }
        if party.state or party.district or party.address:
            field_values["country"] = "India"

        data = PartyAutofillData()
        accepted: list[str] = []
        rejected: list[str] = []
        skipped: list[str] = ["name_suffix"]
        quality_results = []

        for field_name, value in field_values.items():
            if not value:
                if field_name != "country":
                    skipped.append(field_name)
                continue
            quality = self.quality_gate.validate(field_name, value)
            quality_results.append(quality)
            if quality.status in {"accepted", "cleaned"}:
                cleaned = quality.cleaned_value or value
                setattr(
                    data,
                    field_name,
                    PartyAutofillField(
                        value=cleaned,
                        confidence=max(0.0, party.confidence - quality.confidence_penalty),
                        source_page=party.source_page,
                        evidence=party.evidence[:160],
                    ),
                )
                accepted.append(field_name)
            elif quality.status == "skipped":
                skipped.append(f"{field_name}:{quality.reason or 'skipped'}")
            else:
                rejected.append(f"{field_name}:{quality.reason or 'quality_rejected'}")

        if not accepted:
            return None

        if lower_court_source:
            skipped.append("lower_court_source_review_warning_graph_candidates_applied")

        return PartyAutofillResponse(
            document_id=document_id,
            side=side,
            safe_to_apply=True,
            data=data,
            accepted_fields=sorted(set(accepted)),
            rejected_fields=sorted(set(rejected)),
            skipped_fields=sorted(set(skipped)),
            quality_results=quality_results,
        )
