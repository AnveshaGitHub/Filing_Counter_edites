export interface EFilingFetchRequest {
  provisional_no: string;
  provisional_year: string;
}

export interface EFilingFetchResponse {
  source: string;
  document_id?: number | null;
  application_id?: string | null;
  diary_no?: string | null;
  provisional_no: string;
  provisional_year: string;
  status: string;
  message?: string | null;
}
