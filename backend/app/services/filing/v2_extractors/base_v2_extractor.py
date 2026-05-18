from __future__ import annotations

import re
from abc import ABC, abstractmethod

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.field_quality_gate_service import FieldQualityGateService


class BaseV2Extractor(ABC):
    field_keys: set[str] = set()
    allowed_page_types: set[str] = set()

    def __init__(self) -> None:
        self.quality_gate = FieldQualityGateService()

    def clean_space(self, text: str | None) -> str:
        if not text:
            return ""
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def page_text_map(self, pages: list) -> dict[int, str]:
        return {p.page_no: p.text or "" for p in pages}

    def get_allowed_pages(
        self,
        classification: DocumentClassificationResult,
        page_texts: dict[int, str],
    ) -> list[tuple[int, str, str]]:
        out: list[tuple[int, str, str]] = []
        for page in classification.pages:
            if page.page_type in self.allowed_page_types:
                out.append((page.page_no, page.page_type, page_texts.get(page.page_no, "")))
        return out

    def make_candidate(
        self,
        field_key: str,
        value: str,
        confidence: float,
        page_no: int,
        page_type: str,
        evidence: str,
        extractor: str,
    ) -> FieldSpecificCandidate | None:
        cleaned_value = self.clean_space(value)
        if not cleaned_value:
            return None

        quality = self.quality_gate.validate(field_key, cleaned_value)
        if quality.status not in {"accepted", "cleaned"} or not quality.cleaned_value:
            return FieldSpecificCandidate(
                field_key=field_key,
                value=cleaned_value,
                normalized_value=None,
                confidence=max(0.0, confidence - 0.35),
                page_no=page_no,
                page_type=page_type,
                evidence=self.clean_space(evidence)[:240],
                extractor=extractor,
                status="rejected",
                validation_note=quality.reason,
            )

        return FieldSpecificCandidate(
            field_key=field_key,
            value=quality.cleaned_value,
            normalized_value=quality.cleaned_value,
            confidence=confidence,
            page_no=page_no,
            page_type=page_type,
            evidence=self.clean_space(evidence)[:240],
            extractor=extractor,
            status="confirmed" if confidence >= 0.85 else "suggested",
            validation_note=None,
        )

    def dedupe(self, candidates: list[FieldSpecificCandidate]) -> list[FieldSpecificCandidate]:
        best: dict[tuple[str, str], FieldSpecificCandidate] = {}

        for candidate in candidates:
            if candidate.status == "rejected":
                continue

            key = (
                candidate.field_key,
                (candidate.normalized_value or candidate.value).strip().upper(),
            )
            old = best.get(key)
            if old is None or candidate.confidence > old.confidence:
                best[key] = candidate

        return sorted(best.values(), key=lambda c: c.confidence, reverse=True)

    @abstractmethod
    def extract(self, classification: DocumentClassificationResult, pages: list) -> list[FieldSpecificCandidate]:
        raise NotImplementedError
