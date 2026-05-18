from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LayoutWord:
    text: str
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    conf: float | None = None


@dataclass
class LayoutLine:
    text: str
    page_no: int
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    words: list[LayoutWord] = field(default_factory=list)


@dataclass
class PartyBlock:
    side: str
    page_no: int
    label: str
    lines: list[LayoutLine]
    confidence: float = 0.75


@dataclass
class PartyDetail:
    field_key: str
    value: str
    confidence: float
    page_no: int
    evidence: str
