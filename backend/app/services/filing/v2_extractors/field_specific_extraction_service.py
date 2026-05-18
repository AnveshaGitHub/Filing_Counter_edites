from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.schemas.field_specific_extraction import FieldSpecificCandidate
from app.services.filing.candidate_persistence_service import CandidatePersistenceService
from app.services.filing.layout_party_extractor import LayoutAwarePartyDetailExtractor
from app.services.filing.page_classifier_service import PageClassifierService, PageInput
from app.services.filing.v2_extractors.advocate_v2_extractor import AdvocateV2Extractor
from app.services.filing.v2_extractors.case_type_v2_extractor import CaseTypeV2Extractor
from app.services.filing.v2_extractors.list_type_v2_extractor import ListTypeV2Extractor
from app.services.filing.v2_extractors.party_name_v2_extractor import PartyNameV2Extractor
from app.services.filing.v2_extractors.party_type_v2_extractor import PartyTypeV2Extractor

logger = logging.getLogger(__name__)


class FieldSpecificExtractionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.classifier = PageClassifierService(db)
        self.extractors = [
            CaseTypeV2Extractor(),
            ListTypeV2Extractor(),
            PartyNameV2Extractor(),
            AdvocateV2Extractor(),
        ]
        self.party_type_extractor = PartyTypeV2Extractor()

    def load_pages(self, document_id: int) -> list[PageInput]:
        return self.classifier.load_pages_from_db(document_id)

    def extract(self, document_id: int) -> tuple[list[FieldSpecificCandidate], dict]:
        pages = self.load_pages(document_id)
        classification = self.classifier.classify_document(document_id, pages)

        all_candidates: list[FieldSpecificCandidate] = []
        rejected_count = 0

        for extractor in self.extractors:
            try:
                out = extractor.extract(classification, pages)
                all_candidates.extend(out)
            except Exception:
                logger.exception("[V2 EXTRACTOR] %s failed", extractor.__class__.__name__)

        try:
            all_candidates.extend(LayoutAwarePartyDetailExtractor(self.db).extract(document_id))
        except Exception:
            logger.exception("[V2 EXTRACTOR] layout party extractor failed")

        all_candidates.extend(self._case_type_from_filename(document_id))

        party_types = self.party_type_extractor.extract_from_party_candidates(all_candidates)
        all_candidates.extend(party_types)

        deduped = self._dedupe(all_candidates)
        try:
            CandidatePersistenceService(self.db).replace_candidates(document_id, deduped)
        except Exception:
            logger.exception("[V2 EXTRACTOR] candidate persistence failed")

        rejected_count += sum(1 for c in all_candidates if c.status == "rejected")

        debug = {
            "extractor_version": "phase_9_3_v2+phase_9_4_layout_party",
            "v2_candidates_count": len(deduped),
            "rejected_candidates_count": rejected_count,
            "page_types_used": sorted({p.page_type for p in classification.pages if p.page_type}),
        }
        return deduped, debug

    def _case_type_from_filename(self, document_id: int) -> list[FieldSpecificCandidate]:
        try:
            from app.models.local_test_document import LocalTestDocument

            row = self.db.query(LocalTestDocument).filter(LocalTestDocument.id == document_id).first()
            if not row or not row.original_filename:
                return []

            name = row.original_filename.upper()

            for code in ["MCRC", "CRA", "CRR", "WP", "MA", "FA", "SA", "WA", "CONC", "MCC", "RP", "RFA"]:
                if name.startswith(code + "_") or name.startswith(code + "-"):
                    return [
                        FieldSpecificCandidate(
                            field_key="case_type",
                            value=code,
                            normalized_value=code,
                            confidence=0.86,
                            page_no=None,
                            page_type="filename",
                            evidence=row.original_filename,
                            extractor="case_type_v2_filename",
                            status="confirmed",
                        )
                    ]

            return []
        except Exception:
            return []

    def _dedupe(self, candidates: list[FieldSpecificCandidate]) -> list[FieldSpecificCandidate]:
        best: dict[tuple[str, str], FieldSpecificCandidate] = {}
        for cand in candidates:
            if cand.status == "rejected":
                continue
            value = cand.normalized_value or cand.value
            key = (cand.field_key, value.strip().upper())
            old = best.get(key)
            if old is None or cand.confidence > old.confidence:
                best[key] = cand
        return sorted(best.values(), key=lambda c: c.confidence, reverse=True)
