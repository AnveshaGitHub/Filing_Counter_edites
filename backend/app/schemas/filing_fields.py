from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

FieldType = Literal["text", "dropdown", "radio", "checkbox", "number", "mobile"]
FieldStatus = Literal["confirmed", "suggested", "missing", "rejected"]
SourceType = Literal["rule", "regex", "vector_retrieval", "index_section", "llm", "manual", "system"]


class FilingFieldDefinition(BaseModel):
    key: str
    label: str
    field_type: FieldType
    required: bool = False
    section: str
    auto_fill_threshold: float = 0.95
    suggestion_threshold: float = 0.60
    allowed_values: list[str] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)
    source_priority: list[str] = Field(default_factory=list)
    multi_value: bool = False
    notes: str | None = None
