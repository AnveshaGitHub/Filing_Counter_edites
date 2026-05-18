export type FieldStatus = "confirmed" | "suggested" | "missing" | "rejected";

export interface FieldEvidence {
  source_type?: string | null;
  page_from?: number | null;
  page_to?: number | null;
  chunk_id?: string | null;
  text?: string | null;
  validation_notes?: string | null;
}

export interface FieldCandidate {
  value: string;
  normalized_value?: string | null;
  confidence: number;
  status: FieldStatus;
  evidence?: FieldEvidence | null;
}

export interface FieldResult {
  field_key: string;
  field_label: string;
  status: FieldStatus;
  value?: string | null;
  normalized_value?: string | null;
  confidence: number;
  evidence?: FieldEvidence | null;
  suggestions: FieldCandidate[];
}

export interface AdvocateRowResult {
  row_index: number;
  status: FieldStatus;
  confidence: number;
  adv_code?: string | null;
  enrol_no?: string | null;
  enrol_year?: string | null;
  name?: string | null;
  mobile?: string | null;
  remark?: string | null;
  evidence: FieldEvidence[];
  suggestions: Record<string, FieldCandidate[]>;
}

export interface PartyMoreDetailsResult {
  status: FieldStatus;
  confidence: number;
  address?: string | null;
  district?: string | null;
  state?: string | null;
  pincode?: string | null;
  mobile?: string | null;
  email?: string | null;
  evidence: FieldEvidence[];
  suggestions: Record<string, FieldCandidate[]>;
}

export interface FilingGroupedResult {
  core_fields: Record<string, FieldResult>;
  petitioner_fields: Record<string, FieldResult>;
  respondent_fields: Record<string, FieldResult>;
  checkbox_fields: Record<string, FieldResult>;
  advocate_rows: AdvocateRowResult[];
  petitioner_more_details?: PartyMoreDetailsResult | null;
  respondent_more_details?: PartyMoreDetailsResult | null;
}

export interface ExtractionJobSummary {
  extraction_job_id: number;
  document_id: number;
  form_type: string;
  status: string;
  extractor_version: string;
  overall_confidence?: number | null;
  needs_review: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractionResponse {
  job: ExtractionJobSummary;
  fields: FieldResult[];
  grouped?: FilingGroupedResult | null;
  confirmed_count: number;
  suggested_count: number;
  missing_count: number;
  review_flags: string[];
}

export interface ExtractionRunRequest {
  triggered_by?: string | null;
  run_async: boolean;
  force_recompute: boolean;
  form_type: string;
}
