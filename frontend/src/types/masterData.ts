export interface MasterOption {
  code: string;
  label: string;
}

export interface LinkedMasterOption extends MasterOption {
  state_code?: string | null;
  district_code?: string | null;
  tehsil_code?: string | null;
}

export interface MasterListResponse {
  items: MasterOption[];
}

export interface LinkedMasterListResponse {
  items: LinkedMasterOption[];
}

export type CaseTypeMasterResponse = MasterListResponse;
export type SpecialCaseMasterResponse = MasterListResponse;
export type PartyNameSuffixResponse = MasterListResponse;
