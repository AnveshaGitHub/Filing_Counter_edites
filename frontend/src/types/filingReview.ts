export interface ReviewedFieldInput {
  field_key: string;
  field_label: string;
  system_value?: string | null;
  reviewed_value?: string | null;
  confidence?: number | null;
  action_taken: string;
  evidence_text?: string | null;
  source_type?: string | null;
}

export interface CreateReviewSessionRequest {
  extraction_job_id?: number | null;
  reviewed_by?: string | null;
  status?: string;
  submit_ready?: boolean;
  notes?: string | null;
  fields: ReviewedFieldInput[];
}

export interface ReviewSessionSummary {
  reviewed_session_id: number;
  document_id: number;
  extraction_job_id?: number | null;
  reviewed_by?: string | null;
  status: string;
  submit_ready: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewedFieldResponse {
  field_key: string;
  field_label: string;
  system_value?: string | null;
  reviewed_value?: string | null;
  confidence?: number | null;
  action_taken: string;
  evidence_text?: string | null;
  source_type?: string | null;
}

export interface ReviewSessionResponse {
  session: ReviewSessionSummary;
  fields: ReviewedFieldResponse[];
}
