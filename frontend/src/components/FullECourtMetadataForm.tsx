import type { Dispatch, SetStateAction } from "react";

import CollapsibleSection from "./CollapsibleSection";
import type {
  DocumentIndexItem,
  ExtraAdvocateItem,
  ExtraPartyItem,
  FilingFullMetadata,
  IAApplicationItem,
} from "../types/filingFullMetadata";

type MetadataKey = keyof FilingFullMetadata & string;

type FieldConfig = {
  key: MetadataKey;
  label: string;
  multiline?: boolean;
};

type Props = {
  metadata: FilingFullMetadata;
  setMetadata: Dispatch<SetStateAction<FilingFullMetadata>>;
};

const caseDetailsFields: FieldConfig[] = [
  { key: "high_court", label: "High Court" },
  { key: "bench", label: "Bench" },
  { key: "case_type", label: "Case Type" },
  { key: "case_no", label: "Case No" },
  { key: "case_year", label: "Case Year" },
  { key: "filing_no", label: "Filing No" },
  { key: "filing_year", label: "Filing Year" },
  { key: "filing_date", label: "Filing Date" },
  { key: "case_title", label: "Case Title", multiline: true },
  { key: "petitioner_display_name", label: "Petitioner Display Name" },
  { key: "respondent_display_name", label: "Respondent Display Name" },
  { key: "category_text", label: "Category Text" },
  { key: "category_code", label: "Category Code" },
  { key: "sub_category_text", label: "Sub Category Text" },
  { key: "sub_category_code", label: "Sub Category Code" },
  { key: "last_hearing_status", label: "Last Hearing Status" },
  { key: "tentative_hearing_date", label: "Tentative Hearing Date" },
  { key: "last_order", label: "Last Order", multiline: true },
  { key: "heading", label: "Heading" },
  { key: "sub_heading", label: "Sub Heading" },
  { key: "listable_before", label: "Listable Before" },
  { key: "judge1", label: "Judge 1" },
  { key: "judge2", label: "Judge 2" },
  { key: "before_not_before_judge", label: "Before / Not Before Judge" },
  { key: "purpose_of_listing", label: "Purpose of Listing" },
  { key: "list_directly", label: "List Directly" },
  { key: "list_connected_case", label: "List Connected Case" },
  { key: "statutory_information", label: "Statutory Information", multiline: true },
];

const scrutinyFields: FieldConfig[] = [
  { key: "scrutiny_report_no", label: "Scrutiny Report No" },
  { key: "scrutiny_case_type", label: "Scrutiny Case Type" },
  { key: "scrutiny_case_no", label: "Scrutiny Case No" },
  { key: "scrutiny_case_year", label: "Scrutiny Case Year" },
  { key: "scrutiny_subject_heading", label: "Scrutiny Subject Heading" },
  { key: "scrutiny_category", label: "Scrutiny Category" },
  { key: "scrutiny_sub_category", label: "Scrutiny Sub Category" },
  { key: "subject_code", label: "Subject Code" },
  { key: "subject_name", label: "Subject Name" },
  { key: "category_code", label: "Category Code" },
  { key: "category_name", label: "Category Name" },
  { key: "sub_category_code", label: "Sub Category Code" },
  { key: "sub_category_name", label: "Sub Category Name" },
  { key: "provision_of_law", label: "Provision of Law", multiline: true },
  { key: "act", label: "Act" },
  { key: "section", label: "Section" },
  { key: "section_rule_article_regulation", label: "Section / Rule / Article / Regulation" },
  { key: "rule", label: "Rule" },
  { key: "regulation", label: "Regulation" },
  { key: "claim_amount", label: "Claim Amount" },
  { key: "relief_claimed", label: "Relief Claimed", multiline: true },
  { key: "relief_claimed_description", label: "Relief Claimed Description", multiline: true },
  { key: "fixed_for", label: "Fixed For" },
  { key: "pmt_scan_vyapam", label: "PMT / Scan / Vyapam" },
  { key: "impugned_order_description", label: "Impugned Order Description", multiline: true },
  { key: "court_fee_total", label: "Court Fee Total" },
  { key: "filing_defects", label: "Filing Defects", multiline: true },
  { key: "filing_section_note", label: "Filing Section Note", multiline: true },
  { key: "default_description", label: "Default Description", multiline: true },
];

const limitationFields: FieldConfig[] = [
  { key: "case_nature", label: "Case Nature" },
  { key: "limitation_section", label: "Limitation Section" },
  { key: "order_service_report", label: "Order / Service Report" },
  { key: "date_of_order", label: "Date of Order" },
  { key: "date_of_filing", label: "Date of Filing" },
  { key: "copying_date_applied", label: "Copying Date Applied" },
  { key: "delivery_ready_date", label: "Delivery Ready Date" },
  { key: "compliance_period", label: "Compliance Period" },
  { key: "limitation_period", label: "Limitation Period" },
  { key: "limitation_days_calculated", label: "Limitation Days Calculated" },
  { key: "limitation_status", label: "Limitation Status" },
  { key: "holiday_year", label: "Holiday Year" },
  { key: "holiday_adjustment_days", label: "Holiday Adjustment Days" },
];

const lowerCourtFields: FieldConfig[] = [
  { key: "lower_court_type", label: "Lower Court Type" },
  { key: "lower_court_cnr_no", label: "Lower Court CNR No" },
  { key: "lower_court_district", label: "Lower Court District" },
  { key: "lower_court_tehsil", label: "Lower Court Tehsil" },
  { key: "lower_court_case_type", label: "Lower Court Case Type" },
  { key: "lower_court_case_no", label: "Lower Court Case No" },
  { key: "lower_court_new_case_no", label: "Lower Court New Case No" },
  { key: "lower_court_case_year", label: "Lower Court Case Year" },
  { key: "impugned_judgment_date", label: "Impugned Judgment Date" },
  { key: "judge_designation", label: "Judge Designation" },
  { key: "judge_name", label: "Judge Name" },
  { key: "police_station", label: "Police Station" },
  { key: "crime_no", label: "Crime No" },
  { key: "crime_year", label: "Crime Year" },
  { key: "impugned_brief_description", label: "Impugned Brief Description", multiline: true },
  { key: "impugned_subject_law", label: "Impugned Subject Law" },
  { key: "lower_court_document_no", label: "Lower Court Document No" },
  { key: "lower_court_document_year", label: "Lower Court Document Year" },
  { key: "lower_court_ia_no", label: "Lower Court IA No" },
  { key: "lower_court_ia_particular", label: "Lower Court IA Particular" },
  { key: "lower_court_ia_amount", label: "Lower Court IA Amount" },
  { key: "lower_court_ia_filed_by", label: "Lower Court IA Filed By" },
  { key: "lower_court_ia_status", label: "Lower Court IA Status" },
  { key: "lower_court_ia_remark", label: "Lower Court IA Remark", multiline: true },
];

const summaryFields: FieldConfig[] = [
  { key: "total_pages_in_file", label: "Total Pages in File" },
  { key: "petitioner_total_count", label: "Petitioner Total Count" },
  { key: "respondent_total_count", label: "Respondent Total Count" },
  { key: "petitioner_main_advocate", label: "Petitioner Main Advocate" },
  { key: "respondent_main_advocate", label: "Respondent Main Advocate" },
  { key: "petitioner_main_advocate_no", label: "Petitioner Main Advocate No" },
  { key: "petitioner_main_advocate_year", label: "Petitioner Main Advocate Year" },
  { key: "petitioner_main_advocate_mobile", label: "Petitioner Main Advocate Mobile" },
  { key: "petitioner_main_advocate_email", label: "Petitioner Main Advocate Email" },
  { key: "respondent_main_advocate_no", label: "Respondent Main Advocate No" },
  { key: "respondent_main_advocate_year", label: "Respondent Main Advocate Year" },
  { key: "respondent_main_advocate_mobile", label: "Respondent Main Advocate Mobile" },
  { key: "respondent_main_advocate_email", label: "Respondent Main Advocate Email" },
];

const officeFields: FieldConfig[] = [
  { key: "office_report_summary", label: "Office Report Summary", multiline: true },
  { key: "bail_application_details", label: "Bail Application Details", multiline: true },
];

const extraPartyFields: Array<{ key: keyof ExtraPartyItem; label: string }> = [
  { key: "pet_res", label: "Pet / Res" },
  { key: "party_no", label: "Party No" },
  { key: "ind_dept", label: "Individual / Department" },
  { key: "name", label: "Name" },
  { key: "relation", label: "Relation" },
  { key: "father_husband_name", label: "Father / Husband Name" },
  { key: "sex", label: "Sex" },
  { key: "age", label: "Age" },
  { key: "occupation_department", label: "Occupation / Department" },
  { key: "address", label: "Address" },
  { key: "place_city", label: "Place / City" },
  { key: "state", label: "State" },
  { key: "district", label: "District" },
  { key: "pin", label: "PIN" },
  { key: "phone_mobile", label: "Phone / Mobile" },
  { key: "email_id", label: "Email ID" },
  { key: "status", label: "Status" },
];

const advocateFields: Array<{ key: keyof ExtraAdvocateItem; label: string }> = [
  { key: "advocate_no", label: "Advocate No" },
  { key: "advocate_year", label: "Advocate Year" },
  { key: "advocate_name", label: "Advocate Name" },
  { key: "mobile", label: "Mobile" },
  { key: "email", label: "Email" },
  { key: "party_no", label: "Party No" },
  { key: "type", label: "Type" },
  { key: "if_ag", label: "If AG" },
];

const documentIndexFields: Array<{ key: keyof DocumentIndexItem; label: string }> = [
  { key: "serial_no", label: "Serial No" },
  { key: "document_name", label: "Document Name" },
  { key: "page_range", label: "Page Range" },
];

const iaFields: Array<{ key: keyof IAApplicationItem; label: string }> = [
  { key: "ia_no", label: "IA No" },
  { key: "annual_reg_no", label: "Annual Reg No" },
  { key: "particular", label: "Particular" },
  { key: "filed_by", label: "Filed By" },
  { key: "filed_date", label: "Filed Date" },
  { key: "status", label: "Status" },
];

function ScalarField({
  config,
  value,
  onChange,
}: {
  config: FieldConfig;
  value: unknown;
  onChange: (value: string) => void;
}) {
  return (
    <label className={`field ${config.multiline ? "field--wide" : ""}`}>
      <span>{config.label}</span>
      {config.multiline ? (
        <textarea value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)} />
      )}
    </label>
  );
}

function ScalarFields({
  fields,
  metadata,
  setValue,
}: {
  fields: FieldConfig[];
  metadata: FilingFullMetadata;
  setValue: (key: MetadataKey, value: string) => void;
}) {
  return (
    <div className="form-subgrid">
      {fields.map((field) => (
        <ScalarField key={field.key} config={field} value={metadata[field.key]} onChange={(value) => setValue(field.key, value)} />
      ))}
    </div>
  );
}

function RepeatableList<T extends object>({
  title,
  rows,
  fields,
  onChange,
  emptyRow,
}: {
  title: string;
  rows: T[];
  fields: Array<{ key: keyof T & string; label: string }>;
  onChange: (rows: T[]) => void;
  emptyRow: T;
}) {
  const updateRow = (index: number, key: keyof T & string, value: string) => {
    onChange(
      rows.map((row, rowIndex) =>
        rowIndex === index ? ({ ...row, [key]: key === "serial_no" ? Number(value) || null : value } as T) : row
      )
    );
  };

  return (
    <div className="fc-repeatable">
      <div className="fc-repeatable-header">
        <strong>{title}</strong>
        <button type="button" className="btn" onClick={() => onChange([...rows, { ...emptyRow }])}>
          Add Row
        </button>
      </div>
      {rows.length === 0 ? (
        <div className="muted">No rows added.</div>
      ) : (
        rows.map((row, index) => (
          <div className="fc-repeatable-row" key={`${title}-${index}`}>
            <div className="form-subgrid">
              {fields.map((field) => (
                <label className="field" key={field.key}>
                  <span>{field.label}</span>
                  <input
                    value={(row as Record<string, unknown>)[field.key] == null ? "" : String((row as Record<string, unknown>)[field.key])}
                    onChange={(event) => updateRow(index, field.key, event.target.value)}
                  />
                </label>
              ))}
            </div>
            <button type="button" className="btn" onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}>
              Remove Row
            </button>
          </div>
        ))
      )}
    </div>
  );
}

export default function FullECourtMetadataForm({ metadata, setMetadata }: Props) {
  const setValue = (key: MetadataKey, value: string) => {
    setMetadata((prev) => ({ ...prev, [key]: value }));
  };

  const setRows = <T extends object>(key: MetadataKey, rows: T[]) => {
    setMetadata((prev) => ({ ...prev, [key]: rows }));
  };

  return (
    <>
      <CollapsibleSection title="Case Details" defaultOpen>
        <ScalarFields fields={caseDetailsFields} metadata={metadata} setValue={setValue} />
      </CollapsibleSection>

      <CollapsibleSection title="Scrutiny / Subject Metadata">
        <ScalarFields fields={scrutinyFields} metadata={metadata} setValue={setValue} />
      </CollapsibleSection>

      <CollapsibleSection title="Limitation">
        <ScalarFields fields={limitationFields} metadata={metadata} setValue={setValue} />
      </CollapsibleSection>

      <CollapsibleSection title="Lower Court Details">
        <ScalarFields fields={lowerCourtFields} metadata={metadata} setValue={setValue} />
      </CollapsibleSection>

      <CollapsibleSection title="Extra Parties">
        <RepeatableList<ExtraPartyItem>
          title="Extra Parties"
          rows={metadata.extra_parties || []}
          fields={extraPartyFields}
          onChange={(rows) => setRows("extra_parties", rows)}
          emptyRow={{}}
        />
      </CollapsibleSection>

      <CollapsibleSection title="Extra Advocates">
        <RepeatableList<ExtraAdvocateItem>
          title="Petitioner Extra Advocates"
          rows={metadata.petitioner_extra_advocates || []}
          fields={advocateFields}
          onChange={(rows) => setRows("petitioner_extra_advocates", rows)}
          emptyRow={{}}
        />
        <RepeatableList<ExtraAdvocateItem>
          title="Respondent Extra Advocates"
          rows={metadata.respondent_extra_advocates || []}
          fields={advocateFields}
          onChange={(rows) => setRows("respondent_extra_advocates", rows)}
          emptyRow={{}}
        />
      </CollapsibleSection>

      <CollapsibleSection title="Main Filing Modification Summary">
        <ScalarFields fields={summaryFields} metadata={metadata} setValue={setValue} />
      </CollapsibleSection>

      <CollapsibleSection title="Office Report / Documents">
        <ScalarFields fields={officeFields} metadata={metadata} setValue={setValue} />
        <RepeatableList<DocumentIndexItem>
          title="Document Index"
          rows={metadata.document_index || []}
          fields={documentIndexFields}
          onChange={(rows) => setRows("document_index", rows)}
          emptyRow={{}}
        />
        <RepeatableList<IAApplicationItem>
          title="IA Applications"
          rows={metadata.ia_applications || []}
          fields={iaFields}
          onChange={(rows) => setRows("ia_applications", rows)}
          emptyRow={{}}
        />
      </CollapsibleSection>
    </>
  );
}
