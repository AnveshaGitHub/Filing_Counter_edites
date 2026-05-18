from __future__ import annotations

from app.schemas.filing_extraction import AdvocateRowResult, FieldEvidence


def build_advocate_rows(candidates: list[dict], max_rows: int = 2) -> list[AdvocateRowResult]:
    rows: list[AdvocateRowResult] = []

    for idx, item in enumerate(candidates[:max_rows]):
        value = item.get("value") or {}
        row = AdvocateRowResult(
            row_index=idx,
            status="confirmed" if float(item.get("confidence", 0.0)) >= 0.88 else "suggested",
            confidence=float(item.get("confidence", 0.0)),
            adv_code=None,
            enrol_no=value.get("enrol_no"),
            enrol_year=value.get("enrol_year"),
            name=value.get("name"),
            mobile=value.get("mobile"),
            remark=value.get("remark"),
            evidence=[
                FieldEvidence(
                    source_type=item.get("source_type"),
                    page_from=item.get("page_from"),
                    page_to=item.get("page_to"),
                    chunk_id=item.get("chunk_id"),
                    text=item.get("evidence_text"),
                    validation_notes=None,
                )
            ],
            suggestions={},
        )
        rows.append(row)

    while len(rows) < max_rows:
        rows.append(
            AdvocateRowResult(
                row_index=len(rows),
                status="missing",
                confidence=0.0,
                adv_code=None,
                enrol_no=None,
                enrol_year=None,
                name=None,
                mobile=None,
                remark=None,
                evidence=[],
                suggestions={},
            )
        )

    return rows
