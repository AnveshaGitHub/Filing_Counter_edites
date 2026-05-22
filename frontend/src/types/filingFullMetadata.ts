export type FullMetadataScalar = string | null | undefined;

export interface DocumentIndexItem {
  serial_no?: number | null;
  document_name?: string | null;
  page_range?: string | null;
}

export interface IAApplicationItem {
  ia_no?: string | null;
  annual_reg_no?: string | null;
  particular?: string | null;
  filed_by?: string | null;
  filed_date?: string | null;
  status?: string | null;
}

export interface ExtraAdvocateItem {
  advocate_no?: string | null;
  advocate_year?: string | null;
  advocate_name?: string | null;
  mobile?: string | null;
  email?: string | null;
  party_no?: string | null;
  type?: string | null;
  if_ag?: string | null;
}

export interface ExtraPartyItem {
  pet_res?: string | null;
  party_no?: string | null;
  ind_dept?: string | null;
  name?: string | null;
  relation?: string | null;
  father_husband_name?: string | null;
  sex?: string | null;
  age?: string | null;
  occupation_department?: string | null;
  address?: string | null;
  place_city?: string | null;
  state?: string | null;
  district?: string | null;
  pin?: string | null;
  phone_mobile?: string | null;
  email_id?: string | null;
  status?: string | null;
}

export interface FilingFullMetadata {
  [key: string]:
    | FullMetadataScalar
    | boolean
    | number
    | unknown
    | Record<string, unknown>
    | DocumentIndexItem[]
    | IAApplicationItem[]
    | ExtraAdvocateItem[]
    | ExtraPartyItem[];
  document_index?: DocumentIndexItem[];
  ia_applications?: IAApplicationItem[];
  petitioner_extra_advocates?: ExtraAdvocateItem[];
  respondent_extra_advocates?: ExtraAdvocateItem[];
  extra_parties?: ExtraPartyItem[];
  raw_metadata?: Record<string, unknown>;
}

export interface FilingFullMetadataResponse {
  document_id: number;
  metadata: FilingFullMetadata;
}

export interface FilingFullMetadataAutofillResponse {
  document_id: number;
  section: string;
  metadata: FilingFullMetadata;
  notes: string[];
}
