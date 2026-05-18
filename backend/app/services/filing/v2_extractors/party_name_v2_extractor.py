from __future__ import annotations

import re

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.v2_extractors.base_v2_extractor import BaseV2Extractor


class PartyNameV2Extractor(BaseV2Extractor):
    field_keys = {"petitioner_name", "respondent_name"}
    allowed_page_types = {"hc_cause_title", "application_petition", "lower_court_title"}

    PET_LABELS = ["APPLICANT", "PETITIONER", "APPELLANT", "PLAINTIFF"]
    RES_LABELS = ["RESPONDENT", "NON-APPLICANT", "DEFENDANT"]

    BAD_LINE_TOKENS = [
        "subject heading",
        "criminal law",
        "procedure",
        "category",
        "provision of law",
        "court fee",
        "report of cases",
        "particulars of crime",
        "police station",
        "offence u/s",
    ]

    def clean_candidate_text(self, value: str) -> str:
        value = self.clean_space(value)
        value = value.replace("about:blank", "")
        value = re.sub(r"\[[A-Z0-9\-]+\]", "", value)
        value = re.sub(r"\bIN THE HIGH COURT.*$", "", value, flags=re.I)
        value = re.sub(r"\bSubject\b.*$", "", value, flags=re.I)
        value = re.sub(r"\(\s*\d+\s*\)\s*CRIMINAL LAW.*$", "", value, flags=re.I)
        value = re.sub(r"\bPROCEDURE.*$", "", value, flags=re.I)
        value = re.sub(r"\b(S/o|D/o|W/o)\b.*$", "", value, flags=re.I)
        value = re.sub(r"\baged?\s+about\b.*$", "", value, flags=re.I)
        return value.strip(" :-|,.;'\"")

    def line_is_bad(self, line: str) -> bool:
        low = line.lower()
        return any(tok in low for tok in self.BAD_LINE_TOKENS)

    def extract_labelled(self, scan: str, labels: list[str]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        lines = [self.clean_space(x) for x in re.split(r"[\n\r]+", scan)]
        lines = [x for x in lines if x]

        for idx, line in enumerate(lines):
            if self.line_is_bad(line):
                continue
            for label in labels:
                pat = re.compile(rf"\b{re.escape(label)}\b\s*[:\-]?\s*(.+)", re.I)
                match = pat.search(line)
                if match:
                    out.append((match.group(1), line))
                if re.fullmatch(rf".*\b{re.escape(label)}\b\s*[:\-]?\s*$", line, re.I) and idx + 1 < len(lines):
                    out.append((lines[idx + 1], f"{line} {lines[idx + 1]}"))
        return out

    def extract_versus_block(self, scan: str) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        lines = [self.clean_space(x) for x in re.split(r"[\n\r]+", scan)]
        lines = [x for x in lines if x]

        for idx, line in enumerate(lines):
            if re.fullmatch(r"(versus|vs\.?|v/s)", line, re.I) and idx > 0 and idx + 1 < len(lines):
                out.append(("petitioner_name", lines[idx - 1], f"{lines[idx - 1]} {line} {lines[idx + 1]}"))
                out.append(("respondent_name", lines[idx + 1], f"{lines[idx - 1]} {line} {lines[idx + 1]}"))
        return out

    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        page_texts = self.page_text_map(pages)
        candidates: list[FieldSpecificCandidate] = []

        for page_no, page_type, text in self.get_allowed_pages(classification, page_texts):
            scan = text or ""

            for raw, evidence in self.extract_labelled(scan, self.PET_LABELS):
                cleaned = self.clean_candidate_text(raw)
                cand = self.make_candidate(
                    "petitioner_name",
                    cleaned,
                    0.88 if page_type == "hc_cause_title" else 0.76,
                    page_no,
                    page_type,
                    evidence,
                    "party_name_v2_labelled_petitioner",
                )
                if cand:
                    candidates.append(cand)

            for raw, evidence in self.extract_labelled(scan, self.RES_LABELS):
                cleaned = self.clean_candidate_text(raw)
                if "state of madhya pradesh" in cleaned.lower():
                    cleaned = "THE STATE OF MADHYA PRADESH"
                cand = self.make_candidate(
                    "respondent_name",
                    cleaned,
                    0.88 if page_type == "hc_cause_title" else 0.76,
                    page_no,
                    page_type,
                    evidence,
                    "party_name_v2_labelled_respondent",
                )
                if cand:
                    candidates.append(cand)

            for field_key, raw, evidence in self.extract_versus_block(scan):
                cleaned = self.clean_candidate_text(raw)
                if field_key == "respondent_name" and "state of madhya pradesh" in cleaned.lower():
                    cleaned = "THE STATE OF MADHYA PRADESH"
                cand = self.make_candidate(
                    field_key,
                    cleaned,
                    0.78,
                    page_no,
                    page_type,
                    evidence,
                    "party_name_v2_versus_block",
                )
                if cand:
                    candidates.append(cand)

        return self.dedupe(candidates)[:6]
