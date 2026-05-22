from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.services.filing.candidate_persistence_service import CandidatePersistenceService
from app.services.filing.filing_master_validation_service import FilingMasterValidationService
from app.services.filing.filing_metadata_graph_extractor import FilingMetadataGraphExtractor
from app.services.filing.vision_fallback_service import VisionFallbackService


class FilingCandidatePipelineService:
    """OCR candidates + graph candidates + optional vision candidates + validation."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph_extractor = FilingMetadataGraphExtractor(db)
        self.vision_fallback = VisionFallbackService(db)
        self.validator = FilingMasterValidationService()
        self.persistence = CandidatePersistenceService(db)

    def build_candidates(self, document_id: int) -> dict[str, Any]:
        graph_candidates = self._graph_candidates(document_id)
        graph_candidates = [self.validator.validate_candidate(candidate) for candidate in graph_candidates]
        self.persistence.append_candidates(
            document_id=document_id,
            candidates=graph_candidates,
            extractor_prefix="graph_",
        )

        vision_candidates, vision_debug = self.vision_fallback.extract_candidates(document_id)
        vision_candidates = [self.validator.validate_candidate(candidate) for candidate in vision_candidates]
        self.persistence.append_candidates(
            document_id=document_id,
            candidates=vision_candidates,
            extractor_prefix="vision_",
        )

        merged = self.rerank(document_id)
        return {
            "document_id": document_id,
            "graph_candidates": len(graph_candidates),
            "vision_candidates": len(vision_candidates),
            "vision": vision_debug,
            "merged_top": merged[:40],
        }

    def rerank(self, document_id: int) -> list[dict[str, Any]]:
        rows = self.persistence.list_candidates(document_id)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(str(row.get("field_key") or ""), []).append(row)

        merged: list[dict[str, Any]] = []
        for field_key, candidates in grouped.items():
            scored = sorted(candidates, key=self._candidate_rank, reverse=True)
            if not scored:
                continue
            best = dict(scored[0])
            values = {
                str(row.get("normalized_value") or row.get("value") or "").strip().upper()
                for row in scored
                if row.get("value")
            }
            warnings = []
            if len(values) > 1:
                warnings.append("conflicting_candidates")
            if best.get("status") == "rejected":
                warnings.append("best_candidate_rejected")
            best["merge_warnings"] = warnings
            best["candidate_count"] = len(scored)
            best["auto_fill_ready"] = self._auto_fill_ready(best, warnings)
            merged.append(best)

        merged.sort(key=lambda row: (row.get("auto_fill_ready") is True, float(row.get("confidence") or 0.0)), reverse=True)
        return merged

    def _graph_candidates(self, document_id: int) -> list[FieldSpecificCandidate]:
        graph = self.graph_extractor.extract(document_id)
        out: list[FieldSpecificCandidate] = []

        for party in graph.parties:
            prefix = f"party:{party.side}:{party.party_no}"
            page_type = "party_graph"
            if self._is_main_party(party.party_no):
                if party.name:
                    out.append(
                        self._candidate(
                            field_key=f"{party.side}_name",
                            value=party.name,
                            confidence=max(party.confidence, 0.88),
                            page_no=party.source_page,
                            page_type=page_type,
                            evidence=party.evidence,
                            extractor="graph_party_name",
                        )
                    )
                if party.party_type:
                    out.append(
                        self._candidate(
                            field_key=f"{party.side}_party_type",
                            value=party.party_type,
                            confidence=max(party.confidence, 0.86),
                            page_no=party.source_page,
                            page_type=page_type,
                            evidence=party.evidence,
                            extractor="graph_party_type",
                        )
                    )
            for field_name, value in {
                "name": party.name,
                "relation": party.relation,
                "father_husband_name": party.father_husband_name,
                "age": party.age,
                "address": party.present_address or party.address,
                "district": party.district,
                "tehsil": party.tehsil,
                "state": party.state,
                "party_type": party.party_type,
                "mobile": party.phone_mobile,
                "email": party.email_id,
            }.items():
                if value:
                    out.append(
                        self._candidate(
                            field_key=f"{prefix}:{field_name}",
                            value=value,
                            confidence=party.confidence,
                            page_no=party.source_page,
                            page_type=page_type,
                            evidence=party.evidence,
                            extractor="graph_party",
                        )
                    )

        for advocate in graph.advocates:
            prefix = f"advocate:{advocate.side}:{advocate.party_no}"
            if self._is_main_party(advocate.party_no):
                for canonical_key, value in {
                    "advocate_name": advocate.name,
                    "advocate_enrol_no": advocate.enrol_no,
                    "advocate_enrol_year": advocate.enrol_year,
                    "advocate_mobile": advocate.mobile,
                }.items():
                    if value:
                        out.append(
                            self._candidate(
                                field_key=canonical_key,
                                value=value,
                                confidence=advocate.confidence,
                                page_no=advocate.source_page,
                                page_type="advocate_graph",
                                evidence=advocate.evidence,
                                extractor="graph_advocate",
                            )
                        )
                
            for field_name, value in {
                "name": advocate.name,
                "advocate_no": advocate.enrol_no,
                "advocate_year": advocate.enrol_year,
                "mobile": advocate.mobile,
                "email": advocate.email,
            }.items():
                if value:
                    out.append(
                        self._candidate(
                            field_key=f"{prefix}:{field_name}",
                            value=value,
                            confidence=advocate.confidence,
                            page_no=advocate.source_page,
                            page_type="advocate_graph",
                            evidence=advocate.evidence,
                            extractor="graph_advocate",
                        )
                    )

        for field_key, value in graph.lower_court.items():
            if value:
                out.append(
                    self._candidate(
                        field_key=field_key,
                        value=value,
                        confidence=0.82,
                        page_no=None,
                        page_type="lower_court_graph",
                        evidence=value,
                        extractor="graph_lower_court",
                    )
                )

        return out

    def _is_main_party(self, party_no: str) -> bool:
        return str(party_no or "").strip().upper() in {"1", "1."}

    def _candidate(
        self,
        field_key: str,
        value: str,
        confidence: float,
        page_no: int | None,
        page_type: str,
        evidence: str,
        extractor: str,
    ) -> FieldSpecificCandidate:
        return FieldSpecificCandidate(
            field_key=field_key,
            value=value,
            normalized_value=value,
            confidence=confidence,
            page_no=page_no,
            page_type=page_type,
            evidence=(evidence or value)[:300],
            extractor=extractor,
            status="suggested",
            validation_note=None,
        )

    def _candidate_rank(self, row: dict[str, Any]) -> tuple[float, int, int]:
        confidence = float(row.get("confidence") or 0.0)
        extractor = str(row.get("extractor") or "")
        source_weight = 0
        if extractor.startswith("graph_"):
            source_weight = 3
        elif extractor.startswith("vision_"):
            source_weight = 2
        elif "clean_block" in extractor:
            source_weight = 3
        status_weight = 0 if row.get("status") == "rejected" else 1
        return (confidence, source_weight, status_weight)

    def _auto_fill_ready(self, row: dict[str, Any], warnings: list[str]) -> bool:
        if warnings:
            return False
        if row.get("status") == "rejected":
            return False
        if str(row.get("validation_note") or "").startswith("vision_candidate"):
            return False
        return float(row.get("confidence") or 0.0) >= 0.86
