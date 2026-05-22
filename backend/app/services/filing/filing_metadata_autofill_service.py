from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.local_test_document_page import LocalTestDocumentPage
from app.schemas.filing_full_metadata import ExtraAdvocateItem, ExtraPartyItem, FilingFullMetadata
from app.services.filing.filing_candidate_pipeline_service import FilingCandidatePipelineService
from app.services.filing.filing_full_metadata_service import FilingFullMetadataService
from app.services.filing.filing_metadata_graph_extractor import FilingMetadataGraphExtractor
from app.services.filing.v2_extractors.clean_block_extractor import CleanBlockExtractor


class FilingMetadataAutofillService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.metadata_service = FilingFullMetadataService(db)
        self.clean_block = CleanBlockExtractor()
        self.graph_extractor = FilingMetadataGraphExtractor(db)
        self.candidate_pipeline = FilingCandidatePipelineService(db)

    def autofill(self, document_id: int, section: str) -> dict[str, Any]:
        metadata = self.metadata_service.get(document_id)
        notes: list[str] = []
        candidate_debug = self.candidate_pipeline.build_candidates(document_id)

        if section == "additional-parties":
            parties = self.extract_additional_parties(document_id)
            metadata.extra_parties = parties
            notes.append(f"additional_parties:{len(parties)}")
        elif section == "additional-advocates":
            petitioner_rows, respondent_rows = self.extract_additional_advocates(document_id)
            metadata.petitioner_extra_advocates = petitioner_rows
            metadata.respondent_extra_advocates = respondent_rows
            notes.append(f"petitioner_advocates:{len(petitioner_rows)}")
            notes.append(f"respondent_advocates:{len(respondent_rows)}")
        elif section == "lower-court":
            patch = self.extract_lower_court(document_id)
            for key, value in patch.items():
                setattr(metadata, key, value)
            notes.append(f"lower_court_fields:{len(patch)}")
        elif section == "all":
            parties = self.extract_additional_parties(document_id)
            petitioner_rows, respondent_rows = self.extract_additional_advocates(document_id)
            patch = self.extract_lower_court(document_id)
            metadata.extra_parties = parties
            metadata.petitioner_extra_advocates = petitioner_rows
            metadata.respondent_extra_advocates = respondent_rows
            for key, value in patch.items():
                setattr(metadata, key, value)
            notes.extend(
                [
                    f"additional_parties:{len(parties)}",
                    f"petitioner_advocates:{len(petitioner_rows)}",
                    f"respondent_advocates:{len(respondent_rows)}",
                    f"lower_court_fields:{len(patch)}",
                ]
            )
        else:
            raise ValueError("unsupported_autofill_section")

        graph = self.graph_extractor.extract(document_id)
        raw = dict(metadata.raw_metadata or {})
        raw["metadata_autofill"] = {
            "section": section,
            "notes": notes,
            "graph_notes": graph.notes,
            "graph": graph.as_dict(),
            "candidate_pipeline": candidate_debug,
        }
        metadata.raw_metadata = raw
        saved = self.metadata_service.save(document_id, metadata)

        return {
            "document_id": document_id,
            "section": section,
            "metadata": saved,
            "notes": notes,
        }

    def extract_additional_parties(self, document_id: int) -> list[ExtraPartyItem]:
        return self.graph_extractor.additional_party_items(document_id)

    def extract_additional_advocates(self, document_id: int) -> tuple[list[ExtraAdvocateItem], list[ExtraAdvocateItem]]:
        return self.graph_extractor.advocate_items(document_id)

    def extract_lower_court(self, document_id: int) -> dict[str, str]:
        return self.graph_extractor.lower_court_patch(document_id)

    def _page_texts(self, document_id: int) -> list[tuple[int, str]]:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        return [(int(row.page_no), row.ocr_text or "") for row in rows]

    def _best_cause_title_text(self, document_id: int) -> str:
        best: tuple[float, str] = (0.0, "")
        for page_no, text in self._page_texts(document_id):
            score = self.clean_block._page_score(page_no, "hc_cause_title", text)
            if score > best[0]:
                best = (score, text)
        return best[1] if best[0] >= 0.55 else ""

    def _respondent_cause_title_block(self, text: str) -> str:
        lines = self._lines(text)
        start = None
        for idx, line in enumerate(lines):
            if re.match(r"^\s*RESPONDENTS?\s*[:\-]?", line, re.I):
                start = idx
                break
        if start is None:
            return ""

        block: list[str] = []
        for line in lines[start:]:
            if block and re.search(
                r"\b(PUBLIC INTEREST|PARTICULARS OF THE CAUSE|SUBJECT MATTER|AFFIDAVIT|INDEX|LIST OF DOCUMENTS|CRONOLOGICAL|CHRONOLOGICAL)\b",
                line,
                re.I,
            ):
                break
            block.append(line)
        return "\n".join(block)

    def _split_numbered_parties(self, block: str) -> list[dict[str, str]]:
        clean = self._normalize_inline_numbering(block)
        matches = list(re.finditer(r"(?<!\d)(?P<num>\d{1,2})\s*[.)]\s*", clean))
        out: list[dict[str, str]] = []
        for idx, match in enumerate(matches):
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean)
            text = clean[match.end() : end].strip(" ,;:-")
            if text:
                out.append({"party_no": match.group("num"), "text": text})
        return out

    def _normalize_inline_numbering(self, block: str) -> str:
        value = re.sub(r"^\s*RESPONDENTS?\s*[:\-]?\s*", "", block, flags=re.I)
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"([A-Za-z.)])\s+(\d{1,2})\.\s+", r"\1 \2. ", value)
        return value.strip()

    def _party_item(self, side: str, party_no: str, raw: str) -> ExtraPartyItem:
        raw = self._clean_noise(raw)
        name = raw
        relation = ""
        father_husband = ""
        age = ""
        occupation = ""
        address = ""

        rel_match = re.search(r"\b(?P<rel>S/o|D/o|W/o|C/o)\s+(?P<name>[^,]+)", raw, re.I)
        if rel_match:
            relation = rel_match.group("rel")
            father_husband = self._title_name(rel_match.group("name"))
            name = raw[: rel_match.start()].strip(" ,")

        age_match = re.search(r"\baged?\s+(?:about\s+)?(?P<age>\d{1,3})\s*years?\b", raw, re.I)
        if age_match:
            age = age_match.group("age")

        occupation_match = re.search(r"\bOccupation\s+(?P<occupation>[^,]+)", raw, re.I)
        if occupation_match:
            occupation = occupation_match.group("occupation").strip()

        address_match = re.search(r"\bR/o[-:\s]*(?P<address>.+)$", raw, re.I)
        if address_match:
            address = address_match.group("address").strip(" ,")
            name = raw[: address_match.start()].strip(" ,") if not rel_match else name

        name = re.sub(r"\bthrough\b.*$", "", name, flags=re.I)
        name = re.sub(r"\b(revenue|home|police|department|district|tehsil|r/o)\b.*$", "", name, flags=re.I)
        name = name.strip(" ,.;:-")
        if re.search(r"\bState\s+of\s+M\.?\s*P\.?\b", name, re.I):
            name = "State of M.P."
        elif re.search(r"\bState\s+of\s+Madhya\s+Pradesh\b", name, re.I):
            name = "THE STATE OF MADHYA PRADESH"

        district = ""
        district_match = re.search(r"\bDistrict\s+([A-Za-z ]+?)(?:\s*\(|$|\s+Tehsil)", raw, re.I)
        if district_match:
            district = self._title_name(district_match.group(1).strip())

        place_city = ""
        place_match = re.search(r"\b(?:R/o[-:\s]*)?([A-Za-z]+)\s+Tehsil\b", raw, re.I)
        if place_match:
            place_city = self._title_name(place_match.group(1))

        return ExtraPartyItem(
            pet_res=side,
            party_no=party_no,
            ind_dept=self._infer_party_type(name),
            name=self._title_name(name) if name.upper() != name else name,
            relation=relation,
            father_husband_name=father_husband,
            sex="",
            age=age,
            occupation_department=occupation,
            address=address,
            place_city=place_city,
            state="MADHYA PRADESH" if "(M.P" in raw or "M.P." in raw else "",
            district=district,
            pin="",
            phone_mobile=self._first_mobile(raw),
            email_id=self._first_email(raw),
            status="Pending",
        )

    def _is_advocate_page(self, text: str) -> bool:
        low = text.lower()
        return (
            "state bar council" in low
            or "enrollment no" in low
            or "e.no" in low
            or ("do hereby appoint" in low and "advocate" in low)
        )

    def _advocate_side(self, text: str) -> str:
        low = text.lower()
        if "counsel for the respondent" in low or "advocate for respondent" in low:
            return "respondent"
        return "petitioner"

    def _parse_advocate_rows(self, text: str) -> list[ExtraAdvocateItem]:
        lines = self._lines(text)
        out: list[ExtraAdvocateItem] = []
        for idx, line in enumerate(lines):
            match = re.match(r"^\s*(?P<serial>\d{1,2})[.,)]\s+(?P<body>.+)$", line)
            if not match:
                continue
            body = match.group("body")
            if not self._looks_like_advocate_row(body):
                continue
            window = " ".join(lines[idx : min(idx + 3, len(lines))])
            item = self._advocate_item(body=body, window=window)
            if item.advocate_name:
                out.append(item)
        return out

    def _looks_like_advocate_row(self, body: str) -> bool:
        low = body.lower()
        if any(token in low for token in ["index", "copy of", "affidavit", "vakalatnama"]):
            return False
        return bool(re.search(r"\b[A-Z][A-Za-z.]+\s+[A-Z][A-Za-z.]+", body))

    def _advocate_item(self, body: str, window: str) -> ExtraAdvocateItem:
        enrol_match = re.search(r"E\.?\s*No\.?\s*[:.\-]?\s*(?P<no>\d{1,6})\s*/\s*(?P<year>\d{2,4})", window, re.I)
        mobile = self._first_mobile(window)
        email = self._first_email(window)

        name = re.sub(r"E\.?\s*No\.?.*$", "", body, flags=re.I)
        name = re.sub(r"\b\d{10}\b.*$", "", name)
        name = re.sub(r"--\s*do\s*--?|-\s*do\s*-?", "", name, flags=re.I)
        name = re.sub(r"\b(Vidhi|Bhawan|Hall|MPHC|JBP|Sanat)\b.*$", "", name, flags=re.I)
        name = re.sub(r"\b(Dy|Ce|PlPw)\b\s*$", "", name, flags=re.I)
        name = self._title_name(name.strip(" ,.;:-"))

        return ExtraAdvocateItem(
            advocate_no=enrol_match.group("no") if enrol_match else "",
            advocate_year=self._normalize_year(enrol_match.group("year")) if enrol_match else "",
            advocate_name=name,
            mobile=mobile,
            email=email,
            party_no="1",
            type="Petitioner",
            if_ag="No",
        )

    def _dedupe_advocates(self, rows: list[ExtraAdvocateItem]) -> list[ExtraAdvocateItem]:
        best: dict[str, ExtraAdvocateItem] = {}
        for row in rows:
            key = (row.advocate_no or row.advocate_name or "").strip().upper()
            if not key:
                continue
            old = best.get(key)
            if old is None:
                best[key] = row
                continue
            old_score = sum(1 for value in old.model_dump().values() if value)
            new_score = sum(1 for value in row.model_dump().values() if value)
            if new_score > old_score:
                best[key] = row
        return list(best.values())

    def _scrutiny_text(self, document_id: int) -> str:
        for _page_no, text in self._page_texts(document_id):
            low = text.lower()
            if "scrutiny" in low or "subject heading" in low or "provision of law" in low:
                return text
        return ""

    def _line_value(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text or "", re.I)
        return self._clean_noise(match.group(1)) if match else ""

    def _lines(self, text: str) -> list[str]:
        return [line.strip() for line in re.split(r"[\r\n]+", text or "") if line.strip()]

    def _clean_noise(self, value: str) -> str:
        value = re.sub(r"\s+", " ", value or "")
        value = re.sub(r"^[^A-Za-z0-9]+", "", value)
        value = re.sub(r"\b(ceeense|Presensat|Recaiving|Aacietee|DAE)\b", " ", value, flags=re.I)
        return re.sub(r"\s+", " ", value).strip(" ,.;:-")

    def _infer_party_type(self, name: str) -> str:
        low = name.lower()
        if any(token in low for token in ["state of", "collector", "tehsildar", "department", "government"]):
            return "State Department"
        if any(token in low for token in ["company", "limited", "corporation", "society", "trust", "bank"]):
            return "Other Organization"
        return "Individual"

    def _title_name(self, value: str) -> str:
        value = self._clean_noise(value)
        if not value:
            return ""
        if re.search(r"\bM\.?\s*P\.?\b", value, re.I):
            return value
        return " ".join(part.capitalize() if part.isupper() else part for part in value.split())

    def _first_mobile(self, text: str) -> str:
        match = re.search(r"\b[6-9]\d{9}\b", text or "")
        return match.group(0) if match else ""

    def _first_email(self, text: str) -> str:
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text or "")
        return match.group(0) if match else ""

    def _normalize_year(self, year: str) -> str:
        if len(year) == 2:
            return f"20{year}" if int(year) <= 40 else f"19{year}"
        return year
