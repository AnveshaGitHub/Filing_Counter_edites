from __future__ import annotations


def add_conflict_flag(review_flags: list[str], field_key: str, candidates: list[dict]) -> None:
    unique_values = {
        str(c.get("normalized_value") or c.get("value") or "").strip()
        for c in candidates
        if c.get("value")
    }
    unique_values.discard("")
    if len(unique_values) > 1:
        review_flags.append(f"{field_key}:multiple_conflicting_candidates")


def add_low_confidence_flag(
    review_flags: list[str], field_key: str, confidence: float, threshold: float = 0.70
) -> None:
    if confidence < threshold:
        review_flags.append(f"{field_key}:low_confidence")


def add_missing_required_flag(review_flags: list[str], field_key: str, is_missing: bool) -> None:
    if is_missing:
        review_flags.append(f"{field_key}:required_missing")
