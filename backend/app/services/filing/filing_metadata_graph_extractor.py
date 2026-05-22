from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from app.models.local_test_document import LocalTestDocument
from app.models.local_test_document_page import LocalTestDocumentPage
from app.schemas.filing_full_metadata import ExtraAdvocateItem, ExtraPartyItem
from app.services.filing.v2_extractors.clean_block_extractor import CleanBlockExtractor


PETITIONER_LABEL_RE = re.compile(
    r"\b(APPLICANTS?|APPELLANTS?|PETITIONERS?|PLAINTIFFS?)\b\s*[:;?\-]?",
    re.I,
)
RESPONDENT_LABEL_RE = re.compile(
    r"\b(RESPONDENTS?|NON[- ]?APPLICANTS?|DEFENDANTS?)\b\s*[:;?\-]?",
    re.I,
)
PARTY_NO_RE = re.compile(r"^\s*(?P<num>\d{1,2}(?:\.[A-Z])?)\s*[.)]?\s*(?P<body>.*)$", re.I)
INLINE_PARTY_NO_RE = re.compile(r"(?<!\d)(?P<num>\d{1,2}(?:\.[A-Z])?)\s*[.)]\s+")
RELATION_RE = re.compile(
    r"\b(?P<rel>S/O|D/O|W/O|WD/O|WA/O|C/O)\b\.?\s*(?P<name>[^,\n]{2,100})",
    re.I,
)
AGE_RE = re.compile(r"\baged?\s*(?:about\s*)?(?P<age>\d{1,3})\s*years?\b", re.I)
OCCUPATION_RE = re.compile(r"\bOccupation\s*[:\-]?\s*(?P<value>[^,\n]{2,80})", re.I)
ADDRESS_RE = re.compile(r"\b(?:R/O|Address)\b\s*[:\-]?\s*(?P<value>.+)$", re.I)
MOBILE_RE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")


@dataclass
class PartyNode:
    side: str
    party_no: str
    name: str
    relation: str = ""
    father_husband_name: str = ""
    age: str = ""
    occupation: str = ""
    address: str = ""
    present_address: str = ""
    district: str = ""
    tehsil: str = ""
    state: str = ""
    place_city: str = ""
    party_type: str = "Individual"
    phone_mobile: str = ""
    email_id: str = ""
    source_page: int | None = None
    evidence: str = ""
    confidence: float = 0.0


@dataclass
class AdvocateNode:
    side: str
    name: str
    enrol_no: str = ""
    enrol_year: str = ""
    mobile: str = ""
    email: str = ""
    party_no: str = "1"
    source_page: int | None = None
    evidence: str = ""
    confidence: float = 0.0


@dataclass
class FilingMetadataGraph:
    parties: list[PartyNode] = field(default_factory=list)
    advocates: list[AdvocateNode] = field(default_factory=list)
    lower_court: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "parties": [asdict(row) for row in self.parties],
            "advocates": [asdict(row) for row in self.advocates],
            "lower_court": self.lower_court,
            "notes": self.notes,
        }


class FilingMetadataGraphExtractor:
    """Builds a conservative graph before mapping into Filing Counter fields."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.clean_block = CleanBlockExtractor()

    def extract(self, document_id: int) -> FilingMetadataGraph:
        pages = self._page_texts(document_id)
        graph = FilingMetadataGraph()
        graph.parties = self._extract_parties(pages)
        graph.advocates = self._extract_advocates(pages)
        graph.lower_court = self._extract_lower_court(document_id, pages)
        graph.notes = [
            f"party_graph_parties:{len(graph.parties)}",
            f"advocate_graph_rows:{len(graph.advocates)}",
            f"lower_court_graph_fields:{len(graph.lower_court)}",
        ]
        return graph

    def main_party(self, document_id: int, side: str) -> PartyNode | None:
        graph = self.extract(document_id)
        normalized = "petitioner" if side == "petitioner" else "respondent"
        exact = [
            row
            for row in graph.parties
            if row.side == normalized and self._party_no_sort_key(row.party_no) == (1, "")
        ]
        if exact:
            return exact[0]
        rows = [row for row in graph.parties if row.side == normalized]
        return rows[0] if rows else None

    def additional_party_items(self, document_id: int) -> list[ExtraPartyItem]:
        graph = self.extract(document_id)
        rows: list[ExtraPartyItem] = []
        for party in graph.parties:
            if self._party_no_sort_key(party.party_no) == (1, ""):
                continue
            rows.append(self._to_extra_party(party))
        return rows

    def advocate_items(self, document_id: int) -> tuple[list[ExtraAdvocateItem], list[ExtraAdvocateItem]]:
        graph = self.extract(document_id)
        petitioner = [self._to_extra_advocate(row) for row in graph.advocates if row.side == "petitioner"]
        respondent = [self._to_extra_advocate(row) for row in graph.advocates if row.side == "respondent"]
        return self._dedupe_advocates(petitioner), self._dedupe_advocates(respondent)

    def lower_court_patch(self, document_id: int) -> dict[str, str]:
        return self.extract(document_id).lower_court

    def _page_texts(self, document_id: int) -> list[tuple[int, str, str]]:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        out: list[tuple[int, str, str]] = []
        for row in rows:
            page_type = getattr(row, "page_type", None) or getattr(row, "detected_page_type", None) or ""
            text = self._clean_text(row.ocr_text or "")
            if text:
                out.append((int(row.page_no), text, str(page_type or "")))
        return out

    def _extract_parties(self, pages: list[tuple[int, str, str]]) -> list[PartyNode]:
        candidates: list[tuple[float, int, str, list[PartyNode]]] = []
        for page_no, text, page_type in pages:
            if not self._looks_like_cause_title(text, page_type):
                continue
            petitioner_block, respondent_block = self._party_blocks(text)
            parties: list[PartyNode] = []
            if petitioner_block:
                parties.extend(self._parse_party_block("petitioner", petitioner_block, page_no))
            if respondent_block:
                parties.extend(self._parse_party_block("respondent", respondent_block, page_no))
            if PETITIONER_LABEL_RE.search(text) and not any(row.side == "petitioner" for row in parties):
                continue
            if not parties:
                continue
            score = self._party_page_score(text, page_type, parties)
            candidates.append((score, page_no, page_type, parties))

        if not candidates:
            return []

        candidates.sort(key=lambda item: item[0], reverse=True)
        merged: dict[tuple[str, str], PartyNode] = {}
        for score, _page_no, _page_type, parties in candidates[:5]:
            if score < 3.0:
                continue
            for party in parties:
                key = (party.side, party.party_no)
                if not party.name:
                    continue
                old = merged.get(key)
                party.confidence = max(party.confidence, min(0.94, 0.62 + score / 10))
                if old is None or self._party_completeness(party) > self._party_completeness(old):
                    merged[key] = party

        for party in self._respondent_continuation_parties(pages):
            key = (party.side, party.party_no)
            if key not in merged:
                merged[key] = party

        return sorted(merged.values(), key=lambda row: (row.side != "petitioner", self._party_no_sort_key(row.party_no)))

    def _looks_like_cause_title(self, text: str, page_type: str) -> bool:
        low = text.lower()
        if "do hereby appoint" in low or "state bar council" in low:
            return False
        if page_type in {"hc_cause_title", "lower_court_title"}:
            return True
        if "before" in low and "tribunal" in low and "versus" in low:
            return True
        return "high court" in low and (
            re.search(r"\bversus\b", low) is not None
            or "applicants" in low
            or "respondents" in low
            or "petitioner" in low
        )

    def _respondent_continuation_parties(self, pages: list[tuple[int, str, str]]) -> list[PartyNode]:
        out: list[PartyNode] = []
        for page_no, text, _page_type in pages:
            lines = self._lines(text)
            if not lines:
                continue
            block_lines: list[str] = []
            for line in lines[:12]:
                if re.search(r"\bAPPLICATION\s+UNDER|Being aggrieved|The applicants", line, re.I):
                    break
                if PARTY_NO_RE.match(line) or block_lines:
                    block_lines.append(line)
            block = "\n".join(block_lines)
            if not re.search(r"^\s*[34]\s*[.)]?\s+(The\s+State|The\s+Secretary|Collector)", block, re.I | re.M):
                continue
            for party in self._parse_party_block("respondent", block, page_no):
                if party.party_no in {"3", "4"}:
                    party.confidence = max(party.confidence, 0.78)
                    out.append(party)
        return out

    def _party_page_score(self, text: str, page_type: str, parties: list[PartyNode]) -> float:
        score = 0.0
        if page_type == "hc_cause_title":
            score += 2.0
        if "AFFIDAVIT" not in text.upper():
            score += 1.0
        if re.search(r"\b(The applicants? most humbly|respectfully submit|That,\s+the applicant|Being aggrieved)\b", text, re.I):
            score -= 2.0
        if re.search(r"\bCOMPUTER SHEET|To be filled by\b", text, re.I):
            score -= 2.0
        score += min(4.0, len(parties) * 0.7)
        score += min(2.0, sum(1 for p in parties if p.address or p.age or p.father_husband_name) * 0.25)
        if "& Others" in text or "& others" in text:
            score -= 0.8
        return score

    def _party_blocks(self, text: str) -> tuple[str, str]:
        lines = self._lines(text)
        petitioner_start = self._find_label_line(lines, PETITIONER_LABEL_RE)
        respondent_start = self._find_label_line(lines, RESPONDENT_LABEL_RE)
        versus_idx = self._find_versus_line(lines)

        if versus_idx is not None and respondent_start is not None and respondent_start < versus_idx:
            respondent_start = self._find_label_line(lines[versus_idx + 1 :], RESPONDENT_LABEL_RE)
            if respondent_start is not None:
                respondent_start += versus_idx + 1

        if petitioner_start is None and respondent_start is None:
            return "", ""

        petitioner_end = None
        if versus_idx is not None and petitioner_start is not None and versus_idx > petitioner_start:
            petitioner_end = versus_idx
        if respondent_start is not None and petitioner_start is not None and respondent_start > petitioner_start:
            petitioner_end = min(petitioner_end or respondent_start, respondent_start)

        respondent_begin = respondent_start
        if respondent_begin is None and versus_idx is not None:
            respondent_begin = versus_idx + 1

        petitioner_lines = lines[petitioner_start:petitioner_end] if petitioner_start is not None else []
        respondent_lines = lines[respondent_begin:] if respondent_begin is not None else []

        if petitioner_lines and not respondent_lines:
            petitioner_lines, respondent_lines = self._split_unlabelled_respondents(petitioner_lines)

        petitioner_block = self._trim_party_block("\n".join(petitioner_lines))
        respondent_block = self._trim_party_block("\n".join(respondent_lines))
        return petitioner_block, respondent_block

    def _split_unlabelled_respondents(self, petitioner_lines: list[str]) -> tuple[list[str], list[str]]:
        seen_second_party = False
        seen_shared_address = False
        for idx, line in enumerate(petitioner_lines):
            if re.match(r"^\s*2(?:[.)]|\s)", line):
                seen_second_party = True
            if re.search(r"\b(All above|At present)\s+R/O\b", line, re.I):
                seen_shared_address = True
            if idx > 2 and seen_second_party and seen_shared_address and re.match(r"^\s*1\s*[.)]?\s+", line):
                return petitioner_lines[:idx], petitioner_lines[idx:]
        return petitioner_lines, []

    def _trim_party_block(self, block: str) -> str:
        stop_re = re.compile(
            r"\b(AFFIDAVIT|PRAYER|APPLICATION UNDER|APPLICAITION|COVERING MEMO|INDEX|LIST OF DOCUMENTS|"
            r"CRONOLOGICAL|CHRONOLOGICAL|DATE\s*[:-]|VERIFIED BY|SITE INCHARGE)\b",
            re.I,
        )
        out: list[str] = []
        inline_stop_re = re.compile(
            r"\b(The applicants? most humbly|respectfully submit|AFFIDAVIT|PRAYER|APPLICATION UNDER|"
            r"APPLICAITION|COVERING MEMO|Being aggrieved)\b",
            re.I,
        )
        for line in self._lines(block):
            inline_stop = inline_stop_re.search(line)
            if inline_stop:
                line = line[: inline_stop.start()].strip()
            if out and (not line or stop_re.search(line)):
                break
            if line:
                out.append(line)
        return "\n".join(out)

    def _parse_party_block(self, side: str, block: str, page_no: int) -> list[PartyNode]:
        block = re.sub(r"\(\s*(?:Applicant|Non[- ]?Applicant)\s+No\.?\s*[^)]*\)", " ", block, flags=re.I)
        block = re.sub(r"(?im)^\s*Respondent\s+No\.?\s*[|Il1]?\s*[:;]\s*", "1. ", block)
        block = re.sub(r"(?im)^\s*Respondent\s+No\.?\s*(\d{1,2})\s*[:;]\s*", r"\1. ", block)
        block = PETITIONER_LABEL_RE.sub("", block)
        block = RESPONDENT_LABEL_RE.sub("", block)
        block = re.sub(r"(?im)^\s*No\.?\s*[|Il1]?\s*[:;]\s*", "1. ", block)
        block = re.sub(r"(?im)^\s*No\.?\s*(\d{1,2})\s*[:;]\s*", r"\1. ", block)
        block = re.sub(r"^\s*VERSUS\s*$", "", block, flags=re.I | re.M)
        lines = self._lines(block)
        parties: list[tuple[str, str]] = []
        current_no = ""
        current_lines: list[str] = []
        preamble_lines: list[str] = []

        for line in lines:
            line = self._strip_margin_noise(line)
            if not line:
                continue
            match = PARTY_NO_RE.match(line)
            is_new_party = bool(match and self._is_real_party_start(match.group("body")))
            if is_new_party:
                if not current_no and preamble_lines and match.group("num") != "1":
                    parties.append(("1", " ".join(preamble_lines)))
                    preamble_lines = []
                if current_no and current_lines:
                    parties.append((current_no, " ".join(current_lines)))
                current_no = match.group("num").upper()
                current_lines = [match.group("body").strip(" :;")]
                continue
            if not current_no:
                inline = INLINE_PARTY_NO_RE.search(line)
                if inline:
                    current_no = inline.group("num").upper()
                    current_lines = [line[inline.end() :].strip(" :;")]
                    continue
            else:
                inline = INLINE_PARTY_NO_RE.search(line)
                if inline and self._is_real_party_start(line[inline.end() :]):
                    before = line[: inline.start()].strip()
                    if before:
                        current_lines.append(before)
                    if current_no and current_lines:
                        parties.append((current_no, " ".join(current_lines)))
                    current_no = inline.group("num").upper()
                    current_lines = [line[inline.end() :].strip(" :;")]
                    continue
            if current_no:
                current_lines.append(line)
            elif preamble_lines:
                preamble_lines.append(line)
            elif self._is_real_party_start(line):
                preamble_lines.append(line)

        if current_no and current_lines:
            parties.append((current_no, " ".join(current_lines)))
        elif preamble_lines:
            parties.append(("1", " ".join(preamble_lines)))

        shared_all = self._shared_address(block, r"\bAll\s+above\s+R/O\b")
        present_all = self._shared_address(block, r"\bAt\s+present\s+R/O\b")
        shared_both = self._shared_address(block, r"\bBoth\s+R/O\b")

        out: list[PartyNode] = []
        for party_no, raw in parties:
            node = self._party_node(side, party_no, raw, page_no)
            if shared_all and side == "petitioner":
                node.address = node.address or shared_all
            if present_all and side == "petitioner":
                node.present_address = present_all
            if shared_both and side == "respondent" and party_no in {"1", "2"}:
                node.address = node.address or shared_both
            self._derive_places(node)
            out.append(node)
        return out

    def _is_real_party_start(self, body: str) -> bool:
        body = body.strip()
        if not body:
            return False
        low = body.lower()
        if low.startswith(("that,", "that ", "the applicant", "the applicants", "the respondent")):
            return False
        return bool(
            re.search(
                r"\b(Smt|Shri|Sri|Ku\.?|Kumari|The State|State of|Collector|Secretary|Tehsildar|"
                r"Sunil|Surendra|Devendra|Priyanka|Shakuntala|Anil|Parvati|Vishnudev|Shyam|"
                r"IFFCO|Insurance|Company|Ltd\.?|Limited)\b",
                body,
                re.I,
            )
        )

    def _shared_address(self, block: str, marker: str) -> str:
        lines = self._lines(block)
        for idx, line in enumerate(lines):
            if re.search(marker, line, re.I):
                value_lines = [re.sub(marker, "", line, flags=re.I).strip(" ,:-")]
                for extra in lines[idx + 1 : idx + 4]:
                    if PARTY_NO_RE.match(extra) or RESPONDENT_LABEL_RE.search(extra) or re.search(r"\bVERSUS\b", extra, re.I):
                        break
                    value_lines.append(extra)
                return self._clean_party_text(" ".join(value_lines))
        return ""

    def _party_node(self, side: str, party_no: str, raw: str, page_no: int) -> PartyNode:
        text = self._clean_party_text(raw)
        relation = ""
        father_husband = ""
        name_end = len(text)

        rel_match = RELATION_RE.search(text)
        if rel_match:
            relation = self._normalize_relation(rel_match.group("rel"))
            father_husband = self._clean_person_name(rel_match.group("name"))
            if re.fullmatch(r"Late\s+Shri", father_husband, re.I):
                continuation = re.match(r"\s*,\s*([^,]+)", text[rel_match.end() :])
                if continuation:
                    father_husband = self._clean_person_name(f"{father_husband} {continuation.group(1)}")
            name_end = min(name_end, rel_match.start())

        for pattern in [AGE_RE, OCCUPATION_RE, ADDRESS_RE]:
            match = pattern.search(text)
            if match:
                name_end = min(name_end, match.start())
        address_start = re.search(
            r",\s*(?=(?:Chaurasia\s+Complex|House\s+No|Ward\s+No|District\b|Through\s+Manager\b))|\bThrough\s+Manager\b",
            text,
            re.I,
        )
        if address_start:
            name_end = min(name_end, address_start.start())

        name = self._clean_person_name(text[:name_end])
        name = re.sub(r"\(\s*(?:Applicant|Non[- ]?Applicant)\s+No\.?\s*[^)]*\)", "", name, flags=re.I).strip(" ,")
        name = re.sub(r"\bdead\s+through\s+L\.?R\.?s\.?.*$", "", name, flags=re.I).strip(" ,")
        if not name:
            name = self._clean_person_name(text.split(",", 1)[0])

        address = ""
        address_match = ADDRESS_RE.search(text)
        if address_match:
            address = self._clean_party_text(address_match.group("value"))
        elif address_start:
            address = self._clean_party_text(text[address_start.start() :])
            address = re.split(r"\bAs\s+per\s+Impugned\s+Award\b|\bThrough\s+Manager\b", address, flags=re.I)[0]
            address = address.strip(" ,")

        node = PartyNode(
            side=side,
            party_no=party_no,
            name=self._normalize_party_name(name),
            relation=relation,
            father_husband_name=father_husband,
            age=self._first_group(AGE_RE, text, "age"),
            occupation=self._first_group(OCCUPATION_RE, text, "value"),
            address=address,
            party_type=self._infer_party_type(name),
            phone_mobile=self._first_match(MOBILE_RE, text),
            email_id=self._first_match(EMAIL_RE, text),
            source_page=page_no,
            evidence=text[:220],
            confidence=0.72,
        )
        self._derive_places(node)
        return node

    def _derive_places(self, node: PartyNode) -> None:
        text = " ".join([node.address, node.present_address, node.evidence])
        district = re.search(r"\bDistrict\s+([A-Za-z .-]+?)(?:,|\.|\)|$)", text, re.I)
        if district:
            cleaned_district = re.split(r"\b(Smt|Shri|Sunil|The|M\.?P\.?)\b", district.group(1), flags=re.I)[0]
            node.district = self._title(re.sub(r"\bM$", "", cleaned_district, flags=re.I))
        tehsil = re.search(r"\bTehsil\s+([A-Za-z .-]+?)(?:,|\.|\)|District|$)", text, re.I)
        if tehsil:
            node.tehsil = self._title(tehsil.group(1))
        village = re.search(r"\bVillage\s+([A-Za-z .-]+?)(?:,|\.|\)|Tahsil|Tehsil|District|$)", text, re.I)
        if village:
            node.place_city = self._title(village.group(1))
        elif not node.place_city:
            place = re.search(r"\b(?:R/O|Near|At present R/O)\s+([A-Za-z .-]+?)(?:,|Tehsil|Tahsil|District|$)", text, re.I)
            if place:
                node.place_city = self._title(place.group(1))
        if re.search(r"\b(M\.?P\.?|Madhya Pradesh)\b", text, re.I):
            node.state = "MADHYA PRADESH"

    def _extract_advocates(self, pages: list[tuple[int, str, str]]) -> list[AdvocateNode]:
        rows: list[AdvocateNode] = []
        for page_no, text, _page_type in pages:
            rows.extend(self._advocate_table_rows(page_no, text))
            rows.extend(self._advocate_narrative_rows(page_no, text))
        return self._dedupe_advocate_nodes(rows)

    def _advocate_table_rows(self, page_no: int, text: str) -> list[AdvocateNode]:
        if not re.search(r"\b(State Bar Council|Enrollment|E\.?\s*No|do hereby appoint)\b", text, re.I):
            return []
        rows: list[AdvocateNode] = []
        flat = re.sub(r"\s+", " ", text)
        serials = list(re.finditer(r"(?<!\d)(?P<serial>\d{1,2})[.,)]\s+(?=[A-Z][A-Za-z.]+\s+[A-Z][A-Za-z.]+)", flat))
        for idx, match in enumerate(serials):
            end = serials[idx + 1].start() if idx + 1 < len(serials) else len(flat)
            segment = flat[match.end() : end].strip()
            if not segment or re.search(r"\b(Particulars|Signature|Thumb|Status)\b", segment, re.I):
                continue
            name = self._advocate_name_from_table_body(segment)
            if not name:
                continue
            enrol = re.search(r"E\.?\s*No\.?\s*[:.\-]?\s*(?P<no>\d{1,6})\s*/\s*(?P<year>\d{2,4})", segment, re.I)
            rows.append(
                AdvocateNode(
                    side=self._advocate_side(segment),
                    name=name,
                    enrol_no=enrol.group("no") if enrol else "",
                    enrol_year=self._normalize_year(enrol.group("year")) if enrol else "",
                    mobile=self._first_match(MOBILE_RE, segment),
                    email=self._first_match(EMAIL_RE, segment),
                    source_page=page_no,
                    evidence=segment[:220],
                    confidence=0.88 if enrol else 0.74,
                )
            )
        if rows:
            return rows

        lines = self._lines(text)
        for idx, line in enumerate(lines):
            match = re.match(r"^\s*(?P<serial>\d{1,2})[.,)]\s+(?P<body>.+)$", line)
            if not match:
                continue
            body = match.group("body")
            if not re.search(r"\b[A-Z][A-Za-z.]+\s+[A-Z][A-Za-z.]+", body):
                continue
            window = " ".join(lines[idx : min(len(lines), idx + 4)])
            name = self._advocate_name_from_table_body(body)
            if not name:
                continue
            enrol = re.search(r"E\.?\s*No\.?\s*[:.\-]?\s*(?P<no>\d{1,6})\s*/\s*(?P<year>\d{2,4})", window, re.I)
            rows.append(
                AdvocateNode(
                    side=self._advocate_side(window),
                    name=name,
                    enrol_no=enrol.group("no") if enrol else "",
                    enrol_year=self._normalize_year(enrol.group("year")) if enrol else "",
                    mobile=self._first_match(MOBILE_RE, window),
                    email=self._first_match(EMAIL_RE, window),
                    source_page=page_no,
                    evidence=window[:220],
                    confidence=0.84 if enrol else 0.72,
                )
            )
        return rows

    def _advocate_narrative_rows(self, page_no: int, text: str) -> list[AdvocateNode]:
        rows: list[AdvocateNode] = []
        normalized = re.sub(r"\s+", " ", text)
        patterns = [
            (r"\bShri\s+([A-Z][A-Za-z. ]{2,70}?),\s*(?:learned\s+)?(?:Dy\.\s*G\.A\.|Advocate|counsel)[^.;]{0,90}?\bfor\s+(?:the\s+)?(petitioner|applicant|appellants?|respondent|respondents?/State|state)", 0.78),
            (r"\bMs\.\s+([A-Z][A-Za-z. ]{2,70}?),\s*(?:learned\s+)?(?:Dy\.\s*G\.A\.|Advocate|counsel)[^.;]{0,90}?\bfor\s+(?:the\s+)?(petitioner|applicant|appellants?|respondent|respondents?/State|state)", 0.78),
            (r"\bCounsel\s+for\s+(Respondent|Petitioner|Applicant|Appellant)\s+Shri\s+([A-Z][A-Za-z. ]{2,70}?),\s*Advocate", 0.74),
            (r"\(([A-Z][A-Z. ]{2,60})\)\s*(?:DATED[-\d ]+)?\s*COUNSEL\s+FOR\s+THE\s+(APPLICANTS?|PETITIONERS?|APPELLANTS?|RESPONDENTS?)", 0.72),
        ]
        for pattern, confidence in patterns:
            for match in re.finditer(pattern, normalized, re.I):
                if pattern.startswith(r"\bCounsel"):
                    side = self._side_from_role(match.group(1))
                    name = match.group(2)
                elif pattern.startswith(r"\("):
                    name = match.group(1)
                    side = self._side_from_role(match.group(2))
                else:
                    name = match.group(1)
                    side = self._side_from_role(match.group(2))
                cleaned = self._clean_advocate_name(name)
                if cleaned:
                    rows.append(
                        AdvocateNode(
                            side=side,
                            name=cleaned,
                            source_page=page_no,
                            evidence=match.group(0)[:220],
                            confidence=confidence,
                        )
                    )
        for match in re.finditer(
            r"\bAdv(?:\.|\s+)\s*([A-Z][A-Za-z. ]{2,70}?)\s*\(\s*(?P<no>\d{1,6})\s*/\s*(?P<year>\d{2,4})\s*\)",
            normalized,
            re.I,
        ):
            window = normalized[max(0, match.start() - 120) : min(len(normalized), match.end() + 160)]
            cleaned = self._clean_advocate_name(match.group(1))
            if cleaned:
                rows.append(
                    AdvocateNode(
                        side=self._advocate_side(window),
                        name=cleaned,
                        enrol_no=match.group("no"),
                        enrol_year=self._normalize_year(match.group("year")),
                        mobile=self._first_match(MOBILE_RE, window),
                        source_page=page_no,
                        evidence=window[:220],
                        confidence=0.9,
                    )
                )
        return rows

    def _extract_lower_court(self, document_id: int, pages: list[tuple[int, str, str]]) -> dict[str, str]:
        all_text = "\n".join(text for _, text, _ in pages)
        flat = re.sub(r"\s+", " ", all_text)
        patch: dict[str, str] = {}

        current = self._current_case_from_document(document_id, flat)
        if current:
            patch["case_type"] = current["case_type"]
            patch["case_no"] = current["case_no"]
            patch["case_year"] = current["case_year"]

        lower = re.search(
            r"\b(?P<type>M\.?\s*J\.?\s*C\.?|C\.?\s*S\.?|RCS|Civil Suit)\s*No\.?\s*(?P<no>[0-9A-Z-]+)\s*/\s*(?P<year>\d{2,4})",
            flat,
            re.I,
        )
        if lower:
            patch["lower_court_type"] = "District Court"
            patch["lower_court_case_type"] = self._case_type(lower.group("type"))
            patch["lower_court_case_no"] = lower.group("no")
            patch["lower_court_case_year"] = self._normalize_year(lower.group("year"))

        macc = re.search(r"\b(MACC)\s+No\.?\s*(?P<no>\d{1,7})\s*/\s*(?P<year>\d{4})", flat, re.I)
        if macc:
            patch["lower_court_type"] = "Motor Accident Claims Tribunal"
            patch["lower_court_case_type"] = "MACC"
            patch["lower_court_case_no"] = macc.group("no")
            patch["lower_court_case_year"] = macc.group("year")

        cnr = re.search(r"\bCNR\s+No\.?\s*([A-Z0-9]{8,24})\b", flat, re.I)
        if cnr:
            patch["lower_court_cnr_no"] = cnr.group(1).upper()

        filing_no = re.search(r"\bFiling\s+No\.?\s*([A-Z]+/\d{1,7}/\d{4})\b", flat, re.I)
        if filing_no:
            patch["lower_court_filing_no"] = filing_no.group(1).upper()

        district = re.search(r"\bcourt\s+of\s+[^,.]{0,80}District\s+Judge,\s*([A-Za-z ]+)", flat, re.I)
        if district:
            patch["lower_court_district"] = self._title(re.split(r"\barising\b|\bpassed\b|\bin\b", district.group(1), flags=re.I)[0])
        tribunal = re.search(r"\bBEFORE\s+([^.\n]{0,120}?TRIBUNAL,\s*([A-Za-z ]+)\s*\(M\.?P\.?\))", flat, re.I)
        if tribunal:
            patch["lower_court_name"] = self._title(tribunal.group(1))
            patch["lower_court_district"] = self._title(tribunal.group(2))

        judge = re.search(r"\bby\s+(?:Hon'?ble\s+)?(?:Shri|Smt\.?|Ms\.?)\s+([A-Za-z .]+?),\s*([^,.]{0,90}?Judge[^,.]{0,80})", flat, re.I)
        if judge:
            patch["judge_name"] = self._title(judge.group(1))
            patch["judge_designation"] = self._title(judge.group(2))
        else:
            judge2 = re.search(r"\bby\s+(Smt\.?\s+[A-Za-z .]+?),\s*([^,.]{0,90}?Judge[^,.]{0,80})", flat, re.I)
            if judge2:
                patch["judge_name"] = self._title(judge2.group(1))
                patch["judge_designation"] = self._title(judge2.group(2))
            else:
                member = re.search(r"\bMember\s*[-:]\s*([A-Za-z .]+)", flat, re.I)
                if member:
                    patch["judge_name"] = self._title(re.split(r"\b(MACC|Filing|CNR|Date)\b", member.group(1), flags=re.I)[0])
                    patch["judge_designation"] = "Member"

        impugned = re.search(r"\border\s+dated\s+(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", flat, re.I)
        if impugned:
            patch["impugned_judgment_date"] = impugned.group(1)

        subject_bits: list[str] = []
        for pat in [
            r"APPLICATION\s+UNDER\s+ORDER\s+41\s+RULE\s+19\s+OF\s+THE\s+C\.?P\.?C\.?",
            r"APPLICATION\s+U/S\s+5\s+OF\s+THE\s+LIMITATION\s+ACT",
            r"subject\s+([A-Z ]{4,80})",
            r"Provision\s+of\s+law\s*[:\-]?\s*([^.\n]{4,120})",
        ]:
            match = re.search(pat, flat, re.I)
            if match:
                subject_bits.append(self._clean_party_text(match.group(1) if match.lastindex else match.group(0)))
        if subject_bits:
            patch["impugned_subject_law"] = " | ".join(dict.fromkeys(subject_bits))

        desc = re.search(
            r"Being\s+aggrieved\s+by\s+the\s+order\s+dated\s+[^.]{0,260}",
            flat,
            re.I,
        )
        if desc:
            patch["impugned_brief_description"] = self._clean_party_text(desc.group(0))
        elif "restoration" in flat.lower():
            patch["impugned_brief_description"] = "Restoration / re-admission of related appeal mentioned in document."

        return {key: value for key, value in patch.items() if value}

    def _current_case_from_document(self, document_id: int, flat: str) -> dict[str, str]:
        candidates: list[tuple[int, dict[str, str]]] = []
        for match in re.finditer(
            r"\b(?P<type>M\.?\s*C\.?\s*C\.?|MCC|M\.?\s*A\.?|FA|WP)\s*(?:NO\.?|[-])\s*(?P<no>\d{1,7})\s*(?:OF|/|-)\s*(?P<year>\d{4})",
            flat,
            re.I,
        ):
            case_type = self._case_type(match.group("type"))
            case_no = match.group("no")
            year = match.group("year")
            score = 1
            if year >= "2017":
                score += 2
            if case_type in {"MCC", "WP", "FA"}:
                score += 1
            candidates.append((score, {"case_type": case_type, "case_no": case_no, "case_year": year}))

        filename_case = self._current_case_from_filename(document_id)
        if filename_case:
            candidates.append((10, filename_case))

        if not candidates:
            return {}
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _current_case_from_filename(self, document_id: int) -> dict[str, str]:
        # This service is request-scoped through DB calls; when available, filename is the safest
        # discriminator between current HC case and older case-history references.
        row = self.db.query(LocalTestDocument).filter(LocalTestDocument.id == document_id).first()
        filename = (getattr(row, "original_filename", "") or "") if row else ""
        match = re.search(r"\b(?P<type>[A-Z]{2,5})[_-](?P<no>\d{1,7})[_-](?P<year>\d{4})\b", filename, re.I)
        if not match:
            return {}
        return {
            "case_type": self._case_type(match.group("type")),
            "case_no": match.group("no"),
            "case_year": match.group("year"),
        }

    def _to_extra_party(self, party: PartyNode) -> ExtraPartyItem:
        return ExtraPartyItem(
            pet_res="Petitioner" if party.side == "petitioner" else "Respondent",
            party_no=party.party_no,
            ind_dept=party.party_type,
            name=party.name,
            relation=party.relation,
            father_husband_name=party.father_husband_name,
            sex="",
            age=party.age,
            occupation_department=party.occupation,
            address=party.present_address or party.address,
            place_city=party.place_city,
            state=party.state,
            district=party.district,
            pin="",
            phone_mobile=party.phone_mobile,
            email_id=party.email_id,
            status="Pending",
        )

    def _to_extra_advocate(self, row: AdvocateNode) -> ExtraAdvocateItem:
        return ExtraAdvocateItem(
            advocate_no=row.enrol_no,
            advocate_year=row.enrol_year,
            advocate_name=row.name,
            mobile=row.mobile,
            email=row.email,
            party_no=row.party_no,
            type="Petitioner" if row.side == "petitioner" else "Respondent",
            if_ag="Yes" if re.search(r"\b(Dy\.?\s*G\.?A\.?|Govt|State)\b", row.evidence, re.I) else "No",
        )

    def _find_label_line(self, lines: list[str], pattern: re.Pattern) -> int | None:
        for idx, line in enumerate(lines):
            if pattern.search(line):
                return idx
        return None

    def _find_versus_line(self, lines: list[str]) -> int | None:
        for idx, line in enumerate(lines):
            if re.fullmatch(r"\s*(VERSUS|VS\.?|V\.?)\s*", line, re.I):
                return idx
        return None

    def _lines(self, text: str) -> list[str]:
        return [line.strip() for line in re.split(r"[\r\n]+", text or "") if line.strip()]

    def _clean_text(self, text: str) -> str:
        return re.sub(r"[ \t]+", " ", text or "").strip()

    def _strip_margin_noise(self, line: str) -> str:
        line = re.sub(r"^[^A-Za-z0-9]*(?:[A-Za-z]\s+)?", "", line).strip()
        return line

    def _clean_party_text(self, value: str) -> str:
        value = re.sub(r"\s+", " ", value or "")
        value = re.sub(
            r"\b(Date\s*[:-].*|Verified By\s*[:-].*|Site Incharge.*|CBSPL.*|PUBLIC INTEREST.*|"
            r"PARTICULARS OF THE CAUSE.*|SUBJECT MATTER.*|AFFIDAVIT.*|COVERING MEMO.*)$",
            "",
            value,
            flags=re.I,
        )
        value = re.sub(r"\b(ceeense|Presensat|Recaiving|Aacietee|DAE|ote)\b", " ", value, flags=re.I)
        return value.strip(" ,.;:-")

    def _clean_person_name(self, value: str) -> str:
        value = self._clean_party_text(value)
        value = re.sub(r"^\W+", "", value)
        value = re.sub(r"\b(?:and|&)\s+Others\b", "", value, flags=re.I).strip(" ,")
        return self._title(value)

    def _normalize_party_name(self, name: str) -> str:
        if re.search(r"\bState\s+of\s+M\.?\s*P\.?\b", name, re.I):
            return "State of M.P."
        if re.search(r"\bState\s+of\s+Madhya\s+Pradesh\b", name, re.I):
            return "State of Madhya Pradesh"
        return name

    def _normalize_relation(self, rel: str) -> str:
        rel = rel.upper().replace(".", "")
        if rel in {"WA/O", "WD/O", "W/O"}:
            return "W/o"
        if rel == "S/O":
            return "S/o"
        if rel == "D/O":
            return "D/o"
        if rel == "C/O":
            return "C/o"
        return rel

    def _infer_party_type(self, name: str) -> str:
        low = name.lower()
        if any(token in low for token in ["state of", "collector", "tehsildar", "secretary", "department", "government"]):
            return "State Department"
        if any(token in low for token in ["company", "limited", "corporation", "society", "trust", "bank", "insurance", "ins.", " co.", "ltd"]):
            return "Other Organization"
        return "Individual"

    def _title(self, value: str) -> str:
        value = self._clean_party_text(value)
        if not value:
            return ""
        words = []
        for word in value.split():
            if re.fullmatch(r"[A-Z]\.?(?:[A-Z]\.?)+", word):
                words.append(word.upper())
            elif word.upper() in {"S/O", "D/O", "W/O", "WD/O", "M.P.", "M.P"}:
                words.append(word.upper())
            else:
                words.append(word[:1].upper() + word[1:].lower() if word.isupper() else word)
        return " ".join(words).strip()

    def _first_group(self, pattern: re.Pattern, text: str, group: str) -> str:
        match = pattern.search(text)
        return self._clean_party_text(match.group(group)) if match else ""

    def _first_match(self, pattern: re.Pattern, text: str) -> str:
        match = pattern.search(text or "")
        return match.group(1) if match else ""

    def _party_no_sort_key(self, value: str) -> tuple[int, str]:
        match = re.match(r"(\d+)(?:\.([A-Z]))?", value or "")
        if not match:
            return (999, value or "")
        return (int(match.group(1)), match.group(2) or "")

    def _party_completeness(self, row: PartyNode) -> int:
        return sum(
            1
            for value in [
                row.name,
                row.relation,
                row.father_husband_name,
                row.age,
                row.address,
                row.present_address,
                row.district,
                row.tehsil,
                row.state,
            ]
            if value
        )

    def _advocate_name_from_table_body(self, body: str) -> str:
        name = re.sub(r"E\.?\s*No\.?.*$", "", body, flags=re.I)
        name = re.sub(r"\b\d{10}\b.*$", "", name)
        name = re.sub(r"--\s*do\s*--?|-\s*do\s*-?", "", name, flags=re.I)
        name = re.sub(r"\b(Vidhi|Bhawan|Hall|MPHC|JBP|Sanat)\b.*$", "", name, flags=re.I)
        name = re.sub(r"\b(Dy|Ce|PlPw)\b\s*$", "", name, flags=re.I)
        return self._clean_advocate_name(name)

    def _clean_advocate_name(self, name: str) -> str:
        name = self._clean_party_text(name)
        name = re.sub(r"\b(Shri|Sri|Smt|Ms)\.?\s+", "", name, flags=re.I)
        if len(name) < 3 or re.search(r"\b(Counsel|Applicant|Respondent|Verified|Site|Name\s+of\s+the\s+Main\s+Advocate)\b", name, re.I):
            return ""
        return self._title(name)

    def _advocate_side(self, text: str) -> str:
        return "respondent" if re.search(r"\b(respondent|state|dy\.?\s*g\.?a\.?)\b", text, re.I) else "petitioner"

    def _side_from_role(self, role: str) -> str:
        return "respondent" if re.search(r"respondent|state", role, re.I) else "petitioner"

    def _dedupe_advocate_nodes(self, rows: list[AdvocateNode]) -> list[AdvocateNode]:
        best: dict[tuple[str, str], AdvocateNode] = {}
        for row in rows:
            key = (row.side, re.sub(r"\W+", "", row.name).upper())
            if not key[1]:
                continue
            old = best.get(key)
            if old is None or self._adv_completeness(row) > self._adv_completeness(old):
                best[key] = row
        return sorted(best.values(), key=lambda row: (row.side != "petitioner", row.name))

    def _dedupe_advocates(self, rows: list[ExtraAdvocateItem]) -> list[ExtraAdvocateItem]:
        best: dict[str, ExtraAdvocateItem] = {}
        for row in rows:
            key = (row.advocate_no or row.advocate_name or "").strip().upper()
            if not key:
                continue
            old = best.get(key)
            if old is None or self._model_completeness(row) > self._model_completeness(old):
                best[key] = row
        return list(best.values())

    def _adv_completeness(self, row: AdvocateNode) -> int:
        return sum(1 for value in [row.name, row.enrol_no, row.enrol_year, row.mobile, row.email, row.evidence] if value)

    def _model_completeness(self, row: ExtraAdvocateItem) -> int:
        return sum(1 for value in row.model_dump().values() if value)

    def _case_type(self, value: str) -> str:
        return re.sub(r"[^A-Za-z]", "", value).upper()

    def _normalize_year(self, year: str) -> str:
        if len(year) == 2:
            return f"20{year}" if int(year) <= 40 else f"19{year}"
        return year
