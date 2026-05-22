from __future__ import annotations

import re

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.v2_extractors.base_v2_extractor import BaseV2Extractor


class CleanBlockExtractor(BaseV2Extractor):
    field_keys = {
        "case_type",
        "petitioner_name",
        "respondent_name",
        "petitioner_party_type",
        "respondent_party_type",
    }
    allowed_page_types = {
        "hc_cause_title",
        "filing_scrutiny_report",
        "index_page",
        "application_petition",
        "affidavit",
        "unknown",
    }
    use_full_pages = True

    CASE_PATTERNS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"\bM\.?\s*Cr\.?\s*C\.?\b|\bMCRC\b", re.I), "MCRC"),
        (re.compile(r"\bW\.?\s*P\.?\b|\bWP\b", re.I), "WP"),
        (re.compile(r"\bC\.?\s*R\.?\s*A\.?\b|\bCRA\b", re.I), "CRA"),
        (re.compile(r"\bC\.?\s*R\.?\s*R\.?\b|\bCRR\b", re.I), "CRR"),
        (re.compile(r"\bF\.?\s*A\.?\b|\bFA\b", re.I), "FA"),
        (re.compile(r"\bM\.?\s*A\.?\b|\bMA\b", re.I), "MA"),
        (re.compile(r"\b(WA|CONC|MCC|RP|RFA|SA|LPA)\b", re.I), ""),
    ]

    PET_LABEL_RE = re.compile(
        r"^\s*(?:\d+\s*[.)-]?\s*)?(?:PETITIONER|PETITIONERS|APPLICANT|APPLICANTS|APPELLANT|APPELLANTS|PLAINTIFF)\s*[:\-]?\s*(.*)$",
        re.I,
    )
    RES_LABEL_RE = re.compile(
        r"^\s*(?:\d+\s*[.)-]?\s*)?(?:RESPONDENT|RESPONDENTS|NON[-\s]?APPLICANT|DEFENDANT|DEFENDANTS)\s*[:\-]?\s*(.*)$",
        re.I,
    )

    STOP_BLOCK_RE = re.compile(
        r"\b(VERSUS|VS\.?|INDEX|LIST OF DOCUMENTS|AFFIDAVIT|DECLARATION|CRONOLOGICAL|CHRONOLOGICAL|"
        r"PARTICULARS OF|COMPUTER SHEET|NAME OF THE MAIN ADVOCATE|FULL NAME|ENROLL?MENT NO)\b",
        re.I,
    )

    HARD_NEGATIVE_TOKENS = [
        "computer sheet",
        "name of the main advocate",
        "particulars of the lower court",
        "do hereby appoint",
        "state bar council",
        "full name",
        "enrollment no",
    ]
    SOFT_NEGATIVE_TOKENS = [
        "chronological events",
        "cronological events",
        "index",
        "list of documents",
        "affidavit",
        "declaration",
        "that the petitioner",
        "respondent no.",
    ]

    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        page_texts = self.page_text_map(pages)
        ranked_pages = sorted(
            (
                (self._page_score(page.page_no, page.page_type, page_texts.get(page.page_no, "")), page)
                for page in classification.pages
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        usable = [(score, page) for score, page in ranked_pages if score >= 0.55]
        if not usable:
            return []

        candidates: list[FieldSpecificCandidate] = []

        for score, page in usable[:2]:
            text = page_texts.get(page.page_no, "")
            case_type = self._extract_case_type(text)
            if case_type:
                cand = self.make_candidate(
                    "case_type",
                    case_type,
                    min(0.95, 0.84 + score * 0.1),
                    page.page_no,
                    page.page_type,
                    self._evidence(text),
                    "clean_block_case_type",
                )
                if cand:
                    candidates.append(cand)

        best_score, best_page = usable[0]
        best_text = page_texts.get(best_page.page_no, "")
        petitioner_block = self._label_block(best_text, self.PET_LABEL_RE)
        respondent_block = self._label_block(best_text, self.RES_LABEL_RE)

        petitioner_name = self._clean_petitioner_name(petitioner_block)
        respondent_name = self._clean_respondent_name(respondent_block)

        if not petitioner_name or not respondent_name:
            fallback_pet, fallback_res = self._extract_vs_line(best_text)
            petitioner_name = petitioner_name or fallback_pet
            respondent_name = respondent_name or fallback_res

        if petitioner_name:
            cand = self.make_candidate(
                "petitioner_name",
                petitioner_name,
                min(0.94, 0.86 + best_score * 0.08),
                best_page.page_no,
                best_page.page_type,
                petitioner_block or self._evidence(best_text),
                "clean_block_party",
            )
            if cand:
                candidates.append(cand)
                candidates.append(self._party_type_candidate("petitioner_party_type", cand, petitioner_name))

        if respondent_name:
            cand = self.make_candidate(
                "respondent_name",
                respondent_name,
                min(0.94, 0.86 + best_score * 0.08),
                best_page.page_no,
                best_page.page_type,
                respondent_block or self._evidence(best_text),
                "clean_block_party",
            )
            if cand:
                candidates.append(cand)
                candidates.append(self._party_type_candidate("respondent_party_type", cand, respondent_name))

        return self.dedupe([cand for cand in candidates if cand is not None])

    def _page_score(self, page_no: int, page_type: str | None, text: str) -> float:
        low = self.clean_space(text).lower()
        if not low:
            return 0.0

        score = 0.0
        if page_type == "hc_cause_title":
            score += 0.45
        elif page_type == "filing_scrutiny_report":
            score += 0.22
        elif page_type in {"application_petition", "index_page", "affidavit"}:
            score += 0.12

        if "in the high court" in low:
            score += 0.12
        if re.search(r"\bpetitioner[s]?\s*[:\-]?", low):
            score += 0.18
        if re.search(r"\brespondent[s]?\s*[:\-]?", low):
            score += 0.18
        if re.search(r"\b(versus|vs\.?)\b", low):
            score += 0.08
        if "cause title" in low:
            score += 0.18
        if re.search(r"\bs/o\b|\baged\s+about\b|\br/o\b", low):
            score += 0.08

        if page_no > 20:
            score -= 0.25
        for token in self.HARD_NEGATIVE_TOKENS:
            if token in low:
                score -= 0.45
        for token in self.SOFT_NEGATIVE_TOKENS:
            if token in low:
                score -= 0.16

        return max(0.0, min(score, 1.0))

    def _lines(self, text: str) -> list[str]:
        raw_lines = re.split(r"[\r\n]+", text or "")
        return [self.clean_space(line).strip(" |") for line in raw_lines if self.clean_space(line)]

    def _label_block(self, text: str, label_re: re.Pattern) -> str:
        lines = self._lines(text)
        for idx, line in enumerate(lines):
            match = label_re.match(line)
            if not match:
                continue
            block = [match.group(1).strip()]
            for next_line in lines[idx + 1 : idx + 6]:
                if self.STOP_BLOCK_RE.search(next_line):
                    break
                if self.PET_LABEL_RE.match(next_line) or self.RES_LABEL_RE.match(next_line):
                    break
                block.append(next_line)
            return self.clean_space(" ".join(part for part in block if part))
        return ""

    def _extract_case_type(self, text: str) -> str | None:
        head = self.clean_space(text)[:1200]
        for pattern, code in self.CASE_PATTERNS:
            match = pattern.search(head)
            if not match:
                continue
            if code:
                return code
            return re.sub(r"[^A-Za-z]", "", match.group(1)).upper()
        return None

    def _clean_petitioner_name(self, block: str) -> str:
        value = self.clean_space(block)
        value = re.sub(r"\b(S/o|D/o|W/o|C/o|son of|daughter of|wife of)\b.*$", "", value, flags=re.I)
        value = re.sub(r"\baged?\s+about\b.*$", "", value, flags=re.I)
        value = re.sub(r"\boccupation\b.*$", "", value, flags=re.I)
        value = re.sub(r"\br/o\b.*$", "", value, flags=re.I)
        return value.strip(" .,:;-|")

    def _clean_respondent_name(self, block: str) -> str:
        value = self.clean_space(block)
        value = re.sub(r"^\s*\d+\s*[.)-]?\s*", "", value)
        value = re.sub(r"\bthrough\b.*$", "", value, flags=re.I)
        value = re.sub(r"\b(revenue|home|police|department|collector|district|tehsil|r/o)\b.*$", "", value, flags=re.I)
        value = re.sub(r"\s*&\s*(ors?|others)\.?\b.*$", "", value, flags=re.I)
        value = value.strip(" .,:;-|")
        if re.search(r"\bstate\s+of\s+m\.?\s*p\.?\b", value, re.I):
            return "State of M.P."
        if re.search(r"\bstate\s+of\s+madhya\s+pradesh\b", value, re.I):
            return "THE STATE OF MADHYA PRADESH"
        return value

    def _extract_vs_line(self, text: str) -> tuple[str | None, str | None]:
        lines = self._lines(text)
        for idx, line in enumerate(lines):
            if not re.fullmatch(r"(versus|vs\.?|v/s)", line, re.I):
                continue
            prev_line = lines[idx - 1] if idx > 0 else ""
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            petitioner = self._clean_petitioner_name(self.PET_LABEL_RE.sub(r"\1", prev_line))
            respondent = self._clean_respondent_name(self.RES_LABEL_RE.sub(r"\1", next_line))
            return petitioner or None, respondent or None
        return None, None

    def _party_type_candidate(
        self,
        field_key: str,
        source: FieldSpecificCandidate,
        name: str,
    ) -> FieldSpecificCandidate:
        party_type, confidence = self._infer_party_type(name)
        return FieldSpecificCandidate(
            field_key=field_key,
            value=party_type,
            normalized_value=party_type,
            confidence=min(confidence, source.confidence),
            page_no=source.page_no,
            page_type=source.page_type,
            evidence=source.evidence,
            extractor="clean_block_party_type",
            status="confirmed" if min(confidence, source.confidence) >= 0.85 else "suggested",
        )

    def _infer_party_type(self, name: str) -> tuple[str, float]:
        low = name.lower()
        if any(
            token in low
            for token in [
                "state of m.p",
                "state of mp",
                "state of madhya pradesh",
                "government",
                "govt",
                "collector",
                "department",
                "tehsildar",
                "police station",
            ]
        ):
            return "State Department", 0.9
        if any(token in low for token in ["company", "limited", "corporation", "society", "trust", "bank"]):
            return "Other Organization", 0.78
        return "Individual", 0.86 if re.search(r"^[A-Za-z .]{3,80}$", name) else 0.68

    def _evidence(self, text: str) -> str:
        return self.clean_space(text)[:240]
