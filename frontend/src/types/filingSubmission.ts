export interface SubmissionValidationIssue {
  field_key: string;
  message: string;
  severity: string;
}

export interface FilingSubmissionPayload {
  case_type?: string | null;
  list_type?: string | null;
  with_application: boolean;

  petitioner_party_type?: string | null;
  petitioner_name?: string | null;
  hide_party_petitioner: boolean;
  differently_abled_petitioner: boolean;

  respondent_party_type?: string | null;
  respondent_name?: string | null;
  hide_party_respondent: boolean;
  differently_abled_respondent: boolean;

  advocates: Array<Record<string, string | null>>;
}

export interface FilingSubmissionPreviewResponse {
  document_id: number;
  extraction_job_id?: number | null;
  reviewed_session_id?: number | null;
  target_system: string;
  dry_run: boolean;
  ready_for_submit: boolean;
  payload: FilingSubmissionPayload;
  validation_issues: SubmissionValidationIssue[];
  audit_meta: Record<string, unknown>;
}

export interface DryRunSubmissionResponse {
  document_id: number;
  target_system: string;
  dry_run: boolean;
  ready_for_submit: boolean;
  validation_issues: SubmissionValidationIssue[];
  automation_result: Record<string, unknown>;
}
