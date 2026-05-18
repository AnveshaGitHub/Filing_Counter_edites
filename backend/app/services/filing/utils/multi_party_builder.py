from __future__ import annotations

from app.schemas.filing_extraction import FieldCandidate, FieldEvidence


def build_party_suggestions(candidates: list[dict], max_items: int = 5) -> list[FieldCandidate]:
    results: list[FieldCandidate] = []
    seen: set[str] = set()

    for item in candidates:
        value = str(item.get("value") or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)

        results.append(
            FieldCandidate(
                value=value,
                normalized_value=value,
                confidence=float(item.get("confidence", 0.0)),
                status="suggested",
                evidence=FieldEvidence(
                    source_type=item.get("source_type"),
                    page_from=item.get("page_from"),
                    page_to=item.get("page_to"),
                    chunk_id=item.get("chunk_id"),
                    text=item.get("evidence_text"),
                    validation_notes=None,
                ),
            )
        )
        if len(results) >= max_items:
            break

    return results
