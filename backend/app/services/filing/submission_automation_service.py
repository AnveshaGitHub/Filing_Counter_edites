from __future__ import annotations

import os

from app.schemas.filing_submission import FilingSubmissionPreviewResponse, DryRunSubmissionResponse


class SubmissionAutomationService:
    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_REAL_FILING_SUBMIT", "false").strip().lower() == "true"

    def prepare_submission(self, preview: FilingSubmissionPreviewResponse) -> FilingSubmissionPreviewResponse:
        return preview

    def dry_run_submission(self, preview: FilingSubmissionPreviewResponse) -> DryRunSubmissionResponse:
        return DryRunSubmissionResponse(
            document_id=preview.document_id,
            target_system=preview.target_system,
            dry_run=True,
            ready_for_submit=preview.ready_for_submit,
            validation_issues=preview.validation_issues,
            automation_result={
                "status": "dry_run_completed",
                "submitted": False,
                "reason": "Dry run only. Real submission disabled by default.",
                "field_count": len(preview.payload.model_dump()),
            },
        )

    def automate_submission(self, preview: FilingSubmissionPreviewResponse, mode: str = "dry_run") -> DryRunSubmissionResponse:
        if mode != "real_submit" or not self.enabled:
            return self.dry_run_submission(preview)

        return DryRunSubmissionResponse(
            document_id=preview.document_id,
            target_system=preview.target_system,
            dry_run=False,
            ready_for_submit=preview.ready_for_submit,
            validation_issues=preview.validation_issues,
            automation_result={
                "status": "real_submit_not_implemented",
                "submitted": False,
                "reason": "Adapter shell ready; real PHHC submit not enabled in code path yet.",
            },
        )
