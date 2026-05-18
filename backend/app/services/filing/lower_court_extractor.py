from __future__ import annotations

import re

from app.schemas.document_type import LowerCourtCandidate
from app.services.filing.field_quality_gate_service import FieldQualityGateService
from app.services.filing.page_priority_service import PageText


class LowerCourtExtractor:
    CASE_TYPE_RE = re.compile(
        r"\b(CRA|CRR|MCRC|MA|FA|SA|WP|WA|CONC|MCC|MATRF)\s*[-_/ ]?\s*(\d{1,6})\s*[/\- ]\s*(\d{2,4})\b",
        re.I,
    )
    CASE_TYPE_ONLY_RE = re.compile(r"\b(CRA|CRR|MCRC|MA|FA|SA|WP|WA|CONC|MCC|MATRF)\b", re.I)
    DECISION_DATE_RE = re.compile(
        r"(date\s+of\s+decision.*?)(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        re.I,
    )

    def __init__(self) -> None:
        self.quality_gate = FieldQualityGateService()

    def _clean(self, value: str | None) -> str | None:
        if not value:
            return None
        value = re.sub(r"\s+", " ", value).strip(" |,:;-")
        return value or None

    def _candidate(
        self,
        field_key: str,
        value: str | None,
        confidence: float,
        page_no: int,
        evidence: str,
    ) -> LowerCourtCandidate | None:
        value = self._clean(value)
        if not value:
            return None

        if field_key in {"lower_court_case_number", "lower_court_decision_date"}:
            cleaned = value
        else:
            quality = self.quality_gate.validate(field_key, value)
            if quality.status not in {"accepted", "cleaned"} or not quality.cleaned_value:
                return None
            cleaned = quality.cleaned_value

        return LowerCourtCandidate(
            field_key=field_key,
            value=cleaned,
            confidence=confidence,
            page_no=page_no,
            evidence=evidence[:220],
        )

    def extract(self, pages: list[PageText], priority_pages: list[int] | None = None) -> list[LowerCourtCandidate]:
        priority_set = set(priority_pages or [])
        ordered_pages = sorted(
            pages,
            key=lambda page: (0 if page.page_no in priority_set else 1, page.page_no),
        )

        candidates: list[LowerCourtCandidate] = []

        for page in ordered_pages[:12]:
            text = self._clean(page.text) or ""
            low = text.lower()

            case_match = self.CASE_TYPE_RE.search(text)
            if case_match:
                case_type = case_match.group(1).upper()
                candidates.append(
                    LowerCourtCandidate(
                        field_key="case_type",
                        value=case_type,
                        confidence=0.88,
                        page_no=page.page_no,
                        evidence=case_match.group(0),
                    )
                )
                candidates.append(
                    LowerCourtCandidate(
                        field_key="lower_court_case_number",
                        value=f"{case_match.group(2)}/{case_match.group(3)}",
                        confidence=0.78,
                        page_no=page.page_no,
                        evidence=case_match.group(0),
                    )
                )
            else:
                type_match = self.CASE_TYPE_ONLY_RE.search(text)
                if type_match and page.page_no <= 3:
                    candidates.append(
                        LowerCourtCandidate(
                            field_key="case_type",
                            value=type_match.group(1).upper(),
                            confidence=0.62,
                            page_no=page.page_no,
                            evidence=type_match.group(0),
                        )
                    )

            decision_match = self.DECISION_DATE_RE.search(text)
            if decision_match:
                candidate = self._candidate(
                    "lower_court_decision_date",
                    decision_match.group(2),
                    0.72,
                    page.page_no,
                    decision_match.group(0),
                )
                if candidate:
                    candidates.append(candidate)

            if (
                "name of first plaintiff" in low
                or "name of first appellant" in low
                or "first defendant" in low
                or "first respondent" in low
                or page.page_no <= 2
            ):
                candidates.extend(self._extract_title_page_parties(text, page.page_no))

        return self._dedupe(candidates)

    def _extract_title_page_parties(self, text: str, page_no: int) -> list[LowerCourtCandidate]:
        out: list[LowerCourtCandidate] = []
        lines = [self._clean(value) for value in re.split(r"[\n\r]+| {2,}", text)]
        lines = [value for value in lines if value]

        for idx, line in enumerate(lines):
            low = line.lower()

            if low in {"state", "state of madhya pradesh", "the state of madhya pradesh"}:
                candidate = self._candidate(
                    "petitioner_name",
                    "THE STATE OF MADHYA PRADESH",
                    0.66,
                    page_no,
                    line,
                )
                if candidate:
                    out.append(candidate)

            if any(label in low for label in ["plaintiff", "appellant", "applicant"]) and idx > 0:
                prev = lines[idx - 1]
                candidate = self._candidate("petitioner_name", prev, 0.55, page_no, f"{prev} {line}")
                if candidate:
                    out.append(candidate)

            if any(label in low for label in ["defendant", "respondent", "accused"]) and idx > 0:
                prev = lines[idx - 1]
                candidate = self._candidate("respondent_name", prev, 0.55, page_no, f"{prev} {line}")
                if candidate:
                    out.append(candidate)

            if re.search(r"\bvs\b|v/s|versus", low, re.I):
                left_right = re.split(r"\bvs\b|v/s|versus", line, flags=re.I)
                if len(left_right) >= 2:
                    petitioner = self._candidate("petitioner_name", left_right[0], 0.55, page_no, line)
                    respondent = self._candidate("respondent_name", left_right[1], 0.55, page_no, line)
                    if petitioner:
                        out.append(petitioner)
                    if respondent:
                        out.append(respondent)

        state_match = re.search(r"\bState\b", text, re.I)
        if state_match:
            candidate = self._candidate(
                "petitioner_name",
                "THE STATE OF MADHYA PRADESH",
                0.56,
                page_no,
                text[max(0, state_match.start() - 40): state_match.end() + 80],
            )
            if candidate:
                out.append(candidate)

        return out

    def _dedupe(self, candidates: list[LowerCourtCandidate]) -> list[LowerCourtCandidate]:
        best: dict[tuple[str, str], LowerCourtCandidate] = {}
        for candidate in candidates:
            key = (candidate.field_key, candidate.value.upper())
            old = best.get(key)
            if old is None or candidate.confidence > old.confidence:
                best[key] = candidate
        return sorted(best.values(), key=lambda candidate: candidate.confidence, reverse=True)
