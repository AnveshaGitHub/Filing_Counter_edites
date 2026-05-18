export interface PartyAutofillField {
  value?: string | null;
  confidence?: number | null;
  source_page?: number | null;
  evidence?: string | null;
}

export interface PartyAutofillData {
  relation: PartyAutofillField;
  father_or_husband: PartyAutofillField;
  occupation: PartyAutofillField;
  gender: PartyAutofillField;
  date_of_birth: PartyAutofillField;
  age: PartyAutofillField;
  country: PartyAutofillField;
  state: PartyAutofillField;
  district: PartyAutofillField;
  tehsil: PartyAutofillField;
  village: PartyAutofillField;
  phone_mobile: PartyAutofillField;
  email_id: PartyAutofillField;
  pincode: PartyAutofillField;
  address: PartyAutofillField;
  caste: PartyAutofillField;
  identity_proof: PartyAutofillField;
  name_suffix: PartyAutofillField;
}

export interface PartyAutofillResponse {
  document_id: number;
  side: string;
  safe_to_apply: boolean;
  data: PartyAutofillData;
  accepted_fields: string[];
  rejected_fields: string[];
  skipped_fields: string[];
}
