from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.services.filing.field_quality_gate_service import FieldQualityGateService


@dataclass
class ParsedPartyBlock:
    side: str
    page_no: int
    raw_text: str
    fields: dict[str, str]


class OCRTextPartyBlockParser:
    PETITIONER_RE = re.compile(
        r"\b(APPELLANTS?|APPLICANTS?|PETITIONERS?)\s*/?\s*[-:]?\s*",
        re.I,
    )
    PETITIONER_LINE_RE = re.compile(
        r"(?im)(?:^|\n)\s*(APPELLANTS?|APPLICANTS?|PETITIONERS?)\s*/?\s*[-:]?\s*",
    )
    RESPONDENT_RE = re.compile(
        r"\b(RESPONDENTS?|NON[- ]?APPLICANTS?)\s*/?\s*[-:]?\s*",
        re.I,
    )
    RESPONDENT_LINE_RE = re.compile(
        r"(?im)(?:^|\n)\s*(RESPONDENTS?|NON[- ]?APPLICANTS?)\s*/?\s*[-:]?\s*",
    )
    STOP_RE = re.compile(
        r"\b(FIRST APPEAL|MISC\.?\s*APPEAL|PRAYER|FACTS OF THE CASE|INDEX|AFFIDAVIT|CONDONATION|JABALPUR|DATE\s*:)\b",
        re.I,
    )

    def __init__(self) -> None:
        self.gate = FieldQualityGateService()

    def extract_candidates_from_pages(
        self,
        page_texts: list[tuple[int, str]],
    ) -> list[FieldSpecificCandidate]:
        candidates: list[FieldSpecificCandidate] = []

        for page_no, text in page_texts:
            blocks = self.parse_page(page_no, text)
            for block in blocks:
                candidates.extend(self._block_to_candidates(block))

        return self._dedupe(candidates)

    def parse_page(self, page_no: int, text: str | None) -> list[ParsedPartyBlock]:
        if not text:
            return []

        cleaned = self._normalize_text_preserve_lines(text)
        line_starts = self._line_starts(cleaned)
        markers: list[tuple[int, str]] = []

        for match in self.PETITIONER_LINE_RE.finditer(cleaned):
            markers.append((self._block_start_with_previous_line(cleaned, line_starts, match.start(1)), "petitioner"))

        for match in self.RESPONDENT_LINE_RE.finditer(cleaned):
            markers.append((self._block_start_with_previous_line(cleaned, line_starts, match.start(1)), "respondent"))

        markers.sort(key=lambda x: x[0])

        blocks: list[ParsedPartyBlock] = []
        for idx, (start, side) in enumerate(markers):
            end = markers[idx + 1][0] if idx + 1 < len(markers) else len(cleaned)
            raw_block = cleaned[start:end]

            stop = self.STOP_RE.search(raw_block)
            if stop:
                raw_block = raw_block[: stop.start()]

            fields = self._parse_block_fields(side, raw_block)
            if fields:
                blocks.append(
                    ParsedPartyBlock(
                        side=side,
                        page_no=page_no,
                        raw_text=raw_block[:500],
                        fields=fields,
                    )
                )

        return blocks

    def _parse_block_fields(self, side: str, raw_block: str) -> dict[str, str]:
        block = self._remove_labels(raw_block)
        block = self._normalize_text(block)

        fields: dict[str, str] = {}

        relation, father = self._extract_relation(block)
        if relation:
            fields[f"{side}_relation"] = relation
        if father:
            fields[f"{side}_father_or_husband"] = father

        age = self._extract_age(block)
        if age:
            fields[f"{side}_age"] = age

        occupation = self._extract_occupation(block)
        if occupation:
            fields[f"{side}_occupation"] = occupation

        address = self._extract_address(block)
        if address:
            fields[f"{side}_address"] = address

        tehsil = self._extract_tehsil(block)
        if tehsil:
            fields[f"{side}_tehsil"] = tehsil

        district = self._extract_district(block)
        if district:
            fields[f"{side}_district"] = district

        state = self._extract_state(block)
        if state:
            fields[f"{side}_state"] = state

        if not fields:
            return {}

        name = self._extract_name(block)
        if name:
            fields[f"{side}_name"] = name

        return fields

    def _extract_name(self, block: str) -> str | None:
        name_part = re.split(
            r"\b(S/o|W/o|D/o|S\/O|W\/O|D\/O|son of|wife of|daughter of|Aged|Age|Occupation|R/o|resident|Tehsil|District)\b",
            block,
            maxsplit=1,
            flags=re.I,
        )[0]
        name_part = re.sub(r"^\s*[-:()t\s]*\b(VERSUS|VS\.?|V/S)\b\s*", " ", name_part, flags=re.I)
        return self._clean_person_name(name_part)

    def _extract_relation(self, block: str) -> tuple[str | None, str | None]:
        patterns = [
            (r"\b(S/o|S\/O)\s+([^,]+)", "S/o"),
            (r"\b(W/o|W\/O)\s+([^,]+)", "W/o"),
            (r"\b(D/o|D\/O)\s+([^,]+)", "D/o"),
            (r"\bson of\s+([^,]+)", "S/o"),
            (r"\bwife of\s+([^,]+)", "W/o"),
            (r"\bdaughter of\s+([^,]+)", "D/o"),
        ]

        for pattern, relation in patterns:
            match = re.search(pattern, block, flags=re.I)
            if not match:
                continue

            raw_name = match.group(2) if len(match.groups()) >= 2 else match.group(1)
            father = re.split(
                r"\b(Aged|Age|Occupation|R/o|resident|Tehsil|District)\b",
                raw_name,
                maxsplit=1,
                flags=re.I,
            )[0]
            return relation, self._clean_person_name(father)

        return None, None

    def _extract_age(self, block: str) -> str | None:
        patterns = [
            r"\bAged\s+about\s+(\d{1,3})\s+years?",
            r"\bAged\s+(\d{1,3})\s+years?",
            r"\bAge\s*[-:]?\s*(\d{1,3})",
            r"\bage\s+(\d{1,3})",
        ]

        for pattern in patterns:
            match = re.search(pattern, block, flags=re.I)
            if not match:
                continue
            age = int(match.group(1))
            if 0 < age < 120:
                return str(age)

        return None

    def _extract_occupation(self, block: str) -> str | None:
        match = re.search(r"\bOccupation\s*[-:]?\s*([^,]+)", block, flags=re.I)
        if not match:
            return None

        value = re.split(
            r"\b(R/o|resident|Tehsil|District|Age|Aged)\b|(?<![A-Za-z])/o",
            match.group(1),
            maxsplit=1,
            flags=re.I,
        )[0]
        cleaned = self._clean_short(value)
        if cleaned:
            cleaned = re.sub(r"\bHOUSE\s+O[CE]\s+MAKER\b", "HOUSE MAKER", cleaned, flags=re.I)
        return cleaned

    def _extract_address(self, block: str) -> str | None:
        match = re.search(
            r"\b(R/o|Rio|resident of|residing at)\s*[-:]?\s*(.+)|(?<![A-Za-z])/o\s*[-:]?\s*(.+)",
            block,
            flags=re.I,
        )
        if not match:
            return None

        value = match.group(2) or match.group(3)
        value = re.split(
            r"\b(District|Tehsil|Tahsil|FIRST APPEAL|PRAYER|FACTS|AFFIDAVIT|VERSUS|RESPONDENT|APPELLANT)\b",
            value,
            maxsplit=1,
            flags=re.I,
        )[0]
        value = re.sub(r"\s+", " ", value).strip(" ,.-")

        if len(value) < 3:
            return None

        return value[:180]

    def _extract_tehsil(self, block: str) -> str | None:
        match = re.search(
            r"\b(?:Tehsil|Tahsil)\s*&?\s*(?:District)?\s*[-:]?\s*([A-Za-z .-]+)",
            block,
            flags=re.I,
        )
        if not match:
            match = re.search(r"\b(?:P\.?S\.?\s+AND\s+)?(?:Tehsil|Tahsil)\s+([A-Za-z .-]+)", block, flags=re.I)
        if not match:
            return None

        value = match.group(1)
        value = re.split(
            r"\b(District|M\.P\.|FIRST APPEAL|RESPONDENT)\b",
            value,
            maxsplit=1,
            flags=re.I,
        )[0]
        return self._clean_short(value)

    def _extract_district(self, block: str) -> str | None:
        patterns = [
            r"\bDistrict\s*[-:]?\s*([A-Za-z .-]+)",
            r"\bDistrict-([A-Za-z .-]+)",
            r"\bTehsil\s*&\s*District\s*[-:]?\s*([A-Za-z .-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, block, flags=re.I)
            if not match:
                continue

            value = match.group(1)
            mp_match = re.search(r"\b([A-Za-z]{3,40})\s*\(\s*M\.?P\.?\s*\)", value, flags=re.I)
            if mp_match:
                value = mp_match.group(1)
            elif "presented" in value.lower():
                words = re.findall(r"[A-Za-z]{3,40}", value)
                if words:
                    value = words[-1]
            value = re.split(
                r"\b(M\.P\.|FIRST APPEAL|RESPONDENT|APPELLANT)\b",
                value,
                maxsplit=1,
                flags=re.I,
            )[0]
            cleaned = self._clean_short(value)
            if cleaned:
                return cleaned

        return None

    def _extract_state(self, block: str) -> str | None:
        if re.search(r"\bM\.?\s*P\.?\b|\bMadhya Pradesh\b", block, flags=re.I):
            return "MP"
        return None

    def _block_to_candidates(self, block: ParsedPartyBlock) -> list[FieldSpecificCandidate]:
        out: list[FieldSpecificCandidate] = []

        for field_key, value in block.fields.items():
            quality_key = self._quality_key(field_key)
            quality = self.gate.validate(quality_key, value)

            if quality.status == "rejected":
                continue

            final_value = quality.cleaned_value or value
            confidence = 0.86
            if field_key.endswith("_name"):
                confidence = 0.91
            elif field_key.endswith("_age"):
                confidence = 0.88
            elif field_key.endswith("_father_or_husband"):
                confidence = 0.84
            elif field_key.endswith("_address"):
                confidence = 0.76

            out.append(
                FieldSpecificCandidate(
                    field_key=field_key,
                    value=final_value,
                    normalized_value=final_value,
                    confidence=confidence,
                    page_no=block.page_no,
                    page_type="ocr_text_party_block",
                    evidence=block.raw_text[:240],
                    extractor="phase_9_4_1_ocr_text_party_block_parser",
                    status="confirmed" if confidence >= 0.88 else "suggested",
                    validation_note=None,
                )
            )

        return out

    def _quality_key(self, field_key: str) -> str:
        if field_key.endswith("_name"):
            return "petitioner_name" if field_key.startswith("petitioner") else "respondent_name"
        if field_key.endswith("_age"):
            return "age"
        if field_key.endswith("_father_or_husband"):
            return "father_or_husband"
        if field_key.endswith("_relation"):
            return "relation"
        if field_key.endswith("_occupation"):
            return "occupation"
        if field_key.endswith("_address"):
            return "address"
        if field_key.endswith("_district"):
            return "district"
        if field_key.endswith("_tehsil"):
            return "tehsil"
        if field_key.endswith("_state"):
            return "state"
        return field_key

    def _remove_labels(self, value: str) -> str:
        value = self.PETITIONER_RE.sub(" ", value)
        value = self.RESPONDENT_RE.sub(" ", value)
        value = re.sub(
            r"\b(Plaintiff|Defendant|Claimant|Non[- ]?Applicant)\b\s*[-:]?",
            " ",
            value,
            flags=re.I,
        )
        return self._normalize_text(value)

    def _normalize_text(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.replace("Wlo", "W/o").replace("Slo", "S/o").replace("Dlo", "D/o")
        value = re.sub(r"\bHouse\s+Oe\s+Maker\b", "House Maker", value, flags=re.I)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _normalize_text_preserve_lines(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.replace("Wlo", "W/o").replace("Slo", "S/o").replace("Dlo", "D/o")
        value = re.sub(r"\bHouse\s+Oe\s+Maker\b", "House Maker", value, flags=re.I)
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def _clean_person_name(self, value: str | None) -> str | None:
        if not value:
            return None

        value = self._normalize_text(value)
        value = re.sub(r"\[[A-Z0-9\-]+\]", " ", value)
        value = re.sub(r"^(Smt\.?|Shri|Mr\.?|Mrs\.?|Ms\.?)\s+", "", value, flags=re.I)
        value = re.sub(r"^\s*[-:()t\s]*\b(VERSUS|VS\.?|V/S)\b\s+", "", value, flags=re.I)
        value = re.sub(r"[^A-Za-z .]", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" .,-:")

        if not value or len(value) < 2 or len(value) > 80:
            return None

        return value.upper()

    def _line_starts(self, value: str) -> list[int]:
        starts = [0]
        for match in re.finditer(r"\n", value):
            starts.append(match.end())
        return starts

    def _block_start_with_previous_line(self, text: str, line_starts: list[int], start: int) -> int:
        current_line_start = 0
        for line_start in line_starts:
            if line_start <= start:
                current_line_start = line_start
            else:
                break

        previous_line_start = 0
        for line_start in line_starts:
            if line_start < current_line_start:
                previous_line_start = line_start
            else:
                break

        previous_line = text[previous_line_start:current_line_start].strip()
        if (
            previous_line
            and re.search(r"\b(S/o|W/o|D/o|S\/O|W\/O|D\/O)\b", previous_line, flags=re.I)
            and not self.PETITIONER_RE.search(previous_line)
            and not self.RESPONDENT_RE.search(previous_line)
        ):
            return previous_line_start

        return start

    def _clean_short(self, value: str | None) -> str | None:
        if not value:
            return None

        value = self._normalize_text(value)
        value = re.sub(r"[^A-Za-z .-]", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" .,-:")

        if not value or len(value) < 2 or len(value) > 80:
            return None

        return value.upper()

    def _dedupe(self, candidates: list[FieldSpecificCandidate]) -> list[FieldSpecificCandidate]:
        best: dict[tuple[str, str], FieldSpecificCandidate] = {}

        for cand in candidates:
            key = (cand.field_key, (cand.normalized_value or cand.value).upper())
            old = best.get(key)
            if old is None or cand.confidence > old.confidence:
                best[key] = cand

        return sorted(best.values(), key=lambda c: c.confidence, reverse=True)
