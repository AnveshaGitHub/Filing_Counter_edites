from __future__ import annotations

from typing import Iterable

from app.services.filing.utils.page_layout_analyzer import page_priority_multiplier


def top_n_unique(items: Iterable[dict], key: str, n: int) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        value = str(item.get(key) or "")
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(item)
        if len(result) >= n:
            break
    return result


def page_priority_score(page_no: int | None) -> float:
    if page_no is None:
        return 0.0
    if page_no <= 1:
        return 1.0
    if page_no <= 3:
        return 0.95
    if page_no <= 5:
        return 0.85
    if page_no <= 10:
        return 0.70
    return 0.40


def contextual_page_score(
    page_no: int | None,
    page_types: list[str] | None,
    field_key: str,
) -> float:
    return page_priority_score(page_no) * page_priority_multiplier(page_types, field_key)


def source_priority_rank(source_type: str | None) -> int:
    ranks = {
        "index_section": 1,
        "regex": 2,
        "vector_retrieval": 3,
        "llm": 4,
        "system": 5,
    }
    return ranks.get(source_type or "system", 99)


def sort_candidates(candidates: list[dict]) -> list[dict]:
    return sorted(
        candidates,
        key=lambda x: (
            -float(x.get("confidence", 0.0)),
            source_priority_rank(x.get("source_type")),
            (x.get("page_from") or 9999),
        ),
    )
