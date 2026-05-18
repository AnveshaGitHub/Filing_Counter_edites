import type {
  ExtractionResponse,
  FieldResult,
  AdvocateRowResult
} from "../types/filingExtraction";

export type AdvocateRow = {
  advCode: string;
  enrolNo: string;
  enrolYear: string;
  name: string;
  mobile: string;
  remark: string;
};

export type FilingFormState = {
  caseType: string;
  listType: string;
  withApplication: boolean;

  petitionerType: string;
  petitionerName: string;
  hidePartyPetitioner: boolean;
  differentlyAbledPetitioner: boolean;

  respondentType: string;
  respondentName: string;
  hidePartyRespondent: boolean;
  differentlyAbledRespondent: boolean;

  advocates: AdvocateRow[];
};

export const emptyFormState: FilingFormState = {
  caseType: "",
  listType: "",
  withApplication: false,

  petitionerType: "",
  petitionerName: "",
  hidePartyPetitioner: false,
  differentlyAbledPetitioner: false,

  respondentType: "",
  respondentName: "",
  hidePartyRespondent: false,
  differentlyAbledRespondent: false,

  advocates: [
    { advCode: "", enrolNo: "", enrolYear: "", name: "", mobile: "", remark: "" },
    { advCode: "", enrolNo: "", enrolYear: "", name: "", mobile: "", remark: "" }
  ]
};

export function toFieldMap(result: ExtractionResponse): Record<string, FieldResult> {
  return result.fields.reduce((acc, field) => {
    acc[field.field_key] = field;
    return acc;
  }, {} as Record<string, FieldResult>);
}

function boolFromValue(value?: string | null): boolean {
  return String(value || "").toLowerCase() === "true";
}

function buildAdvocateRows(groupedRows?: AdvocateRowResult[] | null): AdvocateRow[] {
  if (!groupedRows || groupedRows.length === 0) {
    return emptyFormState.advocates;
  }

  const rows = groupedRows.slice(0, 2).map((row) => ({
    advCode: row.adv_code || "",
    enrolNo: row.enrol_no || "",
    enrolYear: row.enrol_year || "",
    name: row.name || "",
    mobile: row.mobile || "",
    remark: row.remark || ""
  }));

  while (rows.length < 2) {
    rows.push({ advCode: "", enrolNo: "", enrolYear: "", name: "", mobile: "", remark: "" });
  }

  return rows;
}

export function applyConfirmedExtractionToForm(
  result: ExtractionResponse,
  prev: FilingFormState
): FilingFormState {
  const map = toFieldMap(result);
  const grouped = result.grouped;

  return {
    ...prev,
    caseType:
      map.case_type?.status === "confirmed"
        ? map.case_type.normalized_value || map.case_type.value || prev.caseType
        : prev.caseType,
    listType:
      map.list_type?.status === "confirmed"
        ? map.list_type.normalized_value || map.list_type.value || prev.listType
        : prev.listType,
    withApplication:
      map.with_application?.status === "confirmed"
        ? boolFromValue(map.with_application.normalized_value || map.with_application.value)
        : prev.withApplication,

    petitionerType:
      map.petitioner_party_type?.status === "confirmed"
        ? map.petitioner_party_type.normalized_value || map.petitioner_party_type.value || prev.petitionerType
        : prev.petitionerType,
    petitionerName:
      map.petitioner_name?.status === "confirmed"
        ? map.petitioner_name.value || prev.petitionerName
        : prev.petitionerName,
    hidePartyPetitioner:
      map.hide_party_petitioner?.status === "confirmed"
        ? boolFromValue(map.hide_party_petitioner.normalized_value || map.hide_party_petitioner.value)
        : prev.hidePartyPetitioner,
    differentlyAbledPetitioner:
      map.differently_abled_petitioner?.status === "confirmed"
        ? boolFromValue(map.differently_abled_petitioner.normalized_value || map.differently_abled_petitioner.value)
        : prev.differentlyAbledPetitioner,

    respondentType:
      map.respondent_party_type?.status === "confirmed"
        ? map.respondent_party_type.normalized_value || map.respondent_party_type.value || prev.respondentType
        : prev.respondentType,
    respondentName:
      map.respondent_name?.status === "confirmed"
        ? map.respondent_name.value || prev.respondentName
        : prev.respondentName,
    hidePartyRespondent:
      map.hide_party_respondent?.status === "confirmed"
        ? boolFromValue(map.hide_party_respondent.normalized_value || map.hide_party_respondent.value)
        : prev.hidePartyRespondent,
    differentlyAbledRespondent:
      map.differently_abled_respondent?.status === "confirmed"
        ? boolFromValue(map.differently_abled_respondent.normalized_value || map.differently_abled_respondent.value)
        : prev.differentlyAbledRespondent,

    advocates: buildAdvocateRows(grouped?.advocate_rows)
  };
}
