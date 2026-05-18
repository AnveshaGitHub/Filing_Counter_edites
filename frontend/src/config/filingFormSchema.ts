export type FormFieldControl = "input" | "select" | "radio-group" | "checkbox";

export type FormFieldSchema = {
  key: string;
  label: string;
  control: FormFieldControl;
  suggestionKey?: string;
  options?: Array<{ label: string; value: string }>;
  fullWidth?: boolean;
};

export type FormSectionSchema = {
  key: string;
  title: string;
  fields: FormFieldSchema[];
};

const partyTypeOptions = [
  { label: "Individual", value: "Individual" },
  { label: "State Department", value: "State Department" },
  { label: "Other", value: "Other" },
];

export const filingFormSchema: FormSectionSchema[] = [
  {
    key: "case_details",
    title: "CaseType Bench / Case Details",
    fields: [
      { key: "caseType", label: "Case Type", control: "select", suggestionKey: "case_type", options: [] },
      { key: "listType", label: "List Type", control: "input", suggestionKey: "list_type" },
      { key: "withApplication", label: "With Application", control: "checkbox", fullWidth: true },
    ],
  },
  {
    key: "petitioner",
    title: "Petitioner Individual / Department",
    fields: [
      {
        key: "petitionerType",
        label: "Petitioner Type",
        control: "select",
        suggestionKey: "petitioner_party_type",
        options: partyTypeOptions,
      },
      {
        key: "petitionerName",
        label: "Petitioner Name",
        control: "input",
        suggestionKey: "petitioner_name",
        fullWidth: true,
      },
      { key: "hidePartyPetitioner", label: "Hide Party Petitioner", control: "checkbox" },
      {
        key: "differentlyAbledPetitioner",
        label: "Differently Abled Petitioner",
        control: "checkbox",
      },
    ],
  },
  {
    key: "respondent",
    title: "Respondent Individual / Department",
    fields: [
      {
        key: "respondentType",
        label: "Respondent Type",
        control: "select",
        suggestionKey: "respondent_party_type",
        options: partyTypeOptions,
      },
      {
        key: "respondentName",
        label: "Respondent Name",
        control: "input",
        suggestionKey: "respondent_name",
        fullWidth: true,
      },
      { key: "hidePartyRespondent", label: "Hide Party Respondent", control: "checkbox" },
      {
        key: "differentlyAbledRespondent",
        label: "Differently Abled Respondent",
        control: "checkbox",
      },
    ],
  },
  {
    key: "advocate",
    title: "Advocate",
    fields: [
      { key: "advocates.0.advCode", label: "Advocate Code", control: "input" },
      {
        key: "advocates.0.enrolNo",
        label: "Enrol No",
        control: "input",
        suggestionKey: "advocate_enrol_no",
      },
      {
        key: "advocates.0.enrolYear",
        label: "Enrol Year",
        control: "input",
        suggestionKey: "advocate_enrol_year",
      },
      {
        key: "advocates.0.name",
        label: "Advocate Name",
        control: "input",
        suggestionKey: "advocate_name",
      },
      {
        key: "advocates.0.mobile",
        label: "Mobile",
        control: "input",
        suggestionKey: "advocate_mobile",
      },
      { key: "advocates.0.remark", label: "Remark", control: "input", fullWidth: true },
    ],
  },
];
