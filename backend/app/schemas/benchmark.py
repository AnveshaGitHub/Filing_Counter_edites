from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkGoldFile(BaseModel):
    file_name: str
    document_type: str | None = None
    expected: dict[str, str | None] = Field(default_factory=dict)


class BenchmarkFieldResult(BaseModel):
    field_key: str
    expected: str | None = None
    actual: str | None = None
    status: str
    reason: str | None = None


class BenchmarkEvaluationResponse(BaseModel):
    document_id: int
    file_name: str | None = None
    total_fields: int
    passed_fields: int
    failed_fields: int
    missing_fields: int
    noisy_fields: int
    accuracy: float
    per_field_results: list[BenchmarkFieldResult] = Field(default_factory=list)


class GoldDraftResponse(BaseModel):
    document_id: int
    file_name: str | None = None
    draft_path: str
    approved_gold_path: str
    approved_gold_exists: bool = False
    warning: str | None = None
    draft: BenchmarkGoldFile
