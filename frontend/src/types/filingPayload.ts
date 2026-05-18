export interface FilingFormPayload {
  case_type?: string | null;
  list_type?: string | null;
  with_application: boolean;

  petitioner_name?: string | null;
  petitioner_party_type?: string | null;
  hide_party_petitioner: boolean;
  differently_abled_petitioner: boolean;

  respondent_name?: string | null;
  respondent_party_type?: string | null;
  hide_party_respondent: boolean;
  differently_abled_respondent: boolean;

  advocates: Array<Record<string, string | null>>;
}

export interface FilingPayloadValidationIssue {
  field_key: string;
  message: string;
  severity: string;
}

export interface FilingPayloadResponse {
  document_id: number;
  extraction_job_id?: number | null;
  reviewed_session_id?: number | null;
  payload: FilingFormPayload;
  issues: FilingPayloadValidationIssue[];
  ready_for_submit: boolean;
}
