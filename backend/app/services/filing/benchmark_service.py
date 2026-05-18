from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.schemas.benchmark import (
    BenchmarkEvaluationResponse,
    BenchmarkFieldResult,
    BenchmarkGoldFile,
    GoldDraftResponse,
)


class BenchmarkService:
    NOISE_TOKENS = [
        "subject",
        "criminal law",
        "procedure",
        "section",
        "category",
        "high court",
        "report",
        "about:blank",
        "provision of law",
    ]

    def __init__(self, db: Session) -> None:
        self.db = db
        backend_dir = Path(__file__).resolve().parents[3]
        self.gold_dir = backend_dir / "benchmarks" / "gold"
        self.gold_draft_dir = backend_dir / "benchmarks" / "gold_drafts"
        self.result_dir = backend_dir / "benchmarks" / "results"
        self.gold_dir.mkdir(parents=True, exist_ok=True)
        self.gold_draft_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)

    def list_gold_files(self) -> list[str]:
        return sorted(path.name for path in self.gold_dir.glob("*.json"))

    def load_gold_for_document(self, document_id: int) -> BenchmarkGoldFile | None:
        file_name = self._get_document_file_name(document_id)
        if not file_name:
            return None

        normalized = Path(file_name).stem.lower()
        for path in self.gold_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                gold = BenchmarkGoldFile(**data)
                if Path(gold.file_name).stem.lower() == normalized:
                    return gold
            except Exception:
                continue
        return None

    def evaluate(self, document_id: int) -> BenchmarkEvaluationResponse:
        gold = self.load_gold_for_document(document_id)
        actual = self._get_actual_payload(document_id)

        if not gold:
            file_name = self._get_document_file_name(document_id)
            response = BenchmarkEvaluationResponse(
                document_id=document_id,
                file_name=file_name,
                total_fields=0,
                passed_fields=0,
                failed_fields=0,
                missing_fields=0,
                noisy_fields=0,
                accuracy=0.0,
                per_field_results=[
                    BenchmarkFieldResult(
                        field_key="gold_file",
                        expected=f"backend/benchmarks/gold/{Path(file_name or 'unknown').stem}.json",
                        actual=None,
                        status="missing",
                        reason="approved_gold_file_not_found_generate_draft_then_correct_and_move_to_gold",
                    )
                ],
            )
            self._save_result(document_id, response)
            return response

        results: list[BenchmarkFieldResult] = []
        for field_key, expected_value in gold.expected.items():
            actual_value = actual.get(field_key)
            status, reason = self._compare(expected_value, actual_value)
            results.append(
                BenchmarkFieldResult(
                    field_key=field_key,
                    expected=expected_value,
                    actual=actual_value,
                    status=status,
                    reason=reason,
                )
            )

        total = len(results)
        passed = sum(1 for item in results if item.status == "pass")
        failed = sum(1 for item in results if item.status == "fail")
        missing = sum(1 for item in results if item.status == "missing")
        noisy = sum(1 for item in results if item.status == "noisy")

        response = BenchmarkEvaluationResponse(
            document_id=document_id,
            file_name=gold.file_name,
            total_fields=total,
            passed_fields=passed,
            failed_fields=failed,
            missing_fields=missing,
            noisy_fields=noisy,
            accuracy=round(passed / total, 4) if total else 0.0,
            per_field_results=results,
        )
        self._save_result(document_id, response)
        return response

    def latest(self, document_id: int) -> BenchmarkEvaluationResponse | None:
        path = self.result_dir / f"document_{document_id}.json"
        if not path.exists():
            return None
        return BenchmarkEvaluationResponse(**json.loads(path.read_text(encoding="utf-8")))

    def generate_gold_draft(self, document_id: int, force: bool = False) -> GoldDraftResponse:
        file_name = self._get_document_file_name(document_id)
        if not file_name:
            raise ValueError("document_file_name_not_found")

        file_stem = Path(file_name).stem
        gold_path = self.gold_dir / f"{file_stem}.json"
        draft_path = self.gold_draft_dir / f"{file_stem}.draft.json"
        approved_exists = gold_path.exists()

        if draft_path.exists() and not force:
            data = json.loads(draft_path.read_text(encoding="utf-8"))
            draft = BenchmarkGoldFile(**data)
            return GoldDraftResponse(
                document_id=document_id,
                file_name=file_name,
                draft_path=str(draft_path),
                approved_gold_path=str(gold_path),
                approved_gold_exists=approved_exists,
                warning="draft_already_exists_use_force_true_to_regenerate",
                draft=draft,
            )

        actual_payload = self._get_actual_payload(document_id)
        expected = self._build_expected_draft(actual_payload)

        document_type = None
        try:
            from app.services.filing.page_classifier_service import PageClassifierService

            classification = PageClassifierService(self.db).classify_document_from_db(document_id)
            document_type = classification.document_type
        except Exception:
            document_type = None

        draft = BenchmarkGoldFile(
            file_name=file_name,
            document_type=document_type,
            expected=expected,
        )
        draft_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")

        warning = None
        if approved_exists:
            warning = "approved_gold_already_exists_draft_created_but_evaluation_uses_approved_gold"

        return GoldDraftResponse(
            document_id=document_id,
            file_name=file_name,
            draft_path=str(draft_path),
            approved_gold_path=str(gold_path),
            approved_gold_exists=approved_exists,
            warning=warning,
            draft=draft,
        )

    def _build_expected_draft(self, payload: dict) -> dict[str, str | None]:
        fields = [
            "case_type",
            "list_type",
            "special_case",
            "petitioner_party_type",
            "petitioner_name",
            "respondent_party_type",
            "respondent_name",
            "with_application",
        ]
        expected: dict[str, str | None] = {}

        for key in fields:
            value = payload.get(key)
            if value is None:
                expected[key] = None
            elif isinstance(value, bool):
                expected[key] = str(value)
            else:
                expected[key] = str(value).strip() or None

        advocates = payload.get("advocates")
        if isinstance(advocates, list) and advocates:
            row = advocates[0] or {}
            if isinstance(row, dict):
                expected["advocate_name"] = row.get("name")
                expected["advocate_enrol_no"] = row.get("enrol_no")
                expected["advocate_enrol_year"] = row.get("enrol_year")
                expected["advocate_mobile"] = row.get("mobile")

        return expected

    def _compare(self, expected: str | None, actual: str | None) -> tuple[str, str | None]:
        if expected and not actual:
            return "missing", "actual_missing"
        if actual and self._is_noisy(actual):
            return "noisy", "actual_contains_noise_token"
        if self._norm(expected) == self._norm(actual):
            return "pass", None
        return "fail", "value_mismatch"

    def _norm(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.upper()
        value = value.replace("STATE OF M.P.", "THE STATE OF MADHYA PRADESH")
        value = value.replace("STATE OF MP", "THE STATE OF MADHYA PRADESH")
        value = value.replace("STATE OF MADHYA PRADESH", "THE STATE OF MADHYA PRADESH")
        value = re.sub(r"[^A-Z0-9 ]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _is_noisy(self, value: str) -> bool:
        low = value.lower()
        return any(token in low for token in self.NOISE_TOKENS)

    def _get_document_file_name(self, document_id: int) -> str | None:
        try:
            from app.models.local_test_document import LocalTestDocument

            row = self.db.query(LocalTestDocument).filter(LocalTestDocument.id == document_id).first()
            if row:
                return row.original_filename
        except Exception:
            pass

        try:
            from app.models.document import Document

            row = self.db.query(Document).filter(Document.id == document_id).first()
            if row:
                return getattr(row, "file_name", None) or getattr(row, "title", None)
        except Exception:
            pass

        return None

    def _get_actual_payload(self, document_id: int) -> dict[str, str | None]:
        try:
            from app.services.filing.filing_payload_builder_service import FilingPayloadBuilderService

            payload_response = FilingPayloadBuilderService(self.db).get_filing_payload(document_id)
            payload = payload_response.payload
            if hasattr(payload, "model_dump"):
                return payload.model_dump()
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {}

    def _save_result(self, document_id: int, response: BenchmarkEvaluationResponse) -> None:
        path = self.result_dir / f"document_{document_id}.json"
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
