from __future__ import annotations

from app.schemas.filing_extraction import PartyMoreDetailsResult, FieldEvidence


def build_party_more_details(candidates: list[dict]) -> PartyMoreDetailsResult:
    if not candidates:
        return PartyMoreDetailsResult(status="missing", confidence=0.0)

    best = candidates[0]
    value = best.get("value") or {}

    return PartyMoreDetailsResult(
        status="confirmed" if float(best.get("confidence", 0.0)) >= 0.85 else "suggested",
        confidence=float(best.get("confidence", 0.0)),
        address=value.get("address"),
        district=value.get("district"),
        state=value.get("state"),
        pincode=value.get("pincode"),
        mobile=value.get("mobile"),
        email=value.get("email"),
        evidence=[
            FieldEvidence(
                source_type=best.get("source_type"),
                page_from=best.get("page_from"),
                page_to=best.get("page_to"),
                chunk_id=best.get("chunk_id"),
                text=best.get("evidence_text"),
                validation_notes=None,
            )
        ],
        suggestions={},
    )
