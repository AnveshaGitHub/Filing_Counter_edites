import type { FilingFullMetadata } from "../../types/filingFullMetadata";
import { Field, Panel, SearchStrip, SelectField, TextArea } from "./shared";

type Props = {
  documentId?: number;
  metadata: FilingFullMetadata;
  set: (key: string, value: unknown) => void;
  onAutofill: (section: "lower-court") => Promise<void>;
  autofilling?: boolean;
};

function valueOf(metadata: FilingFullMetadata, key: string): string {
  const value = metadata[key];
  return typeof value === "string" ? value : "";
}

export default function LowerCourtTab({ documentId, metadata, set, onAutofill, autofilling = false }: Props) {
  return (
    <>
      <SearchStrip metadata={metadata} set={set} buttonText="Fetch Details" />

      <Panel title="Lower Court Details">
        <div className="button-row">
          <button
            type="button"
            className="phhc-primary-btn"
            disabled={!documentId || autofilling}
            onClick={() => onAutofill("lower-court")}
          >
            {autofilling ? "Autofilling..." : "Autofill Lower Court Details"}
          </button>
        </div>
        <div className="phhc-grid phhc-grid-4">
          <SelectField label="Court Type" value={valueOf(metadata, "lower_court_type")} onChange={(value) => set("lower_court_type", value)} options={["District Court", "High Court", "Other"]} />
          <Field label="CNR No." value={valueOf(metadata, "lower_court_cnr_no")} onChange={(value) => set("lower_court_cnr_no", value)} />
          <Field label="District" value={valueOf(metadata, "lower_court_district")} onChange={(value) => set("lower_court_district", value)} />
          <Field label="Tehsil" value={valueOf(metadata, "lower_court_tehsil")} onChange={(value) => set("lower_court_tehsil", value)} />
          <Field label="Case Type" value={valueOf(metadata, "lower_court_case_type")} onChange={(value) => set("lower_court_case_type", value)} />
          <Field label="Case No." value={valueOf(metadata, "lower_court_case_no")} onChange={(value) => set("lower_court_case_no", value)} />
          <Field label="New Case No." value={valueOf(metadata, "lower_court_new_case_no")} onChange={(value) => set("lower_court_new_case_no", value)} />
          <Field label="Year" value={valueOf(metadata, "lower_court_case_year")} onChange={(value) => set("lower_court_case_year", value)} />
          <Field label="Date of Impugned Judgment/Order/Award" value={valueOf(metadata, "impugned_judgment_date")} onChange={(value) => set("impugned_judgment_date", value)} />
          <Field label="Judge Designation" value={valueOf(metadata, "judge_designation")} onChange={(value) => set("judge_designation", value)} />
          <Field label="Judge Name" value={valueOf(metadata, "judge_name")} onChange={(value) => set("judge_name", value)} />
          <Field label="Police Station" value={valueOf(metadata, "police_station")} onChange={(value) => set("police_station", value)} />
          <Field label="Crime No." value={valueOf(metadata, "crime_no")} onChange={(value) => set("crime_no", value)} />
          <Field label="Crime Year" value={valueOf(metadata, "crime_year")} onChange={(value) => set("crime_year", value)} />
          <TextArea label="Brief Desc. of Impugned Order/Judgment/Award" value={valueOf(metadata, "impugned_brief_description")} onChange={(value) => set("impugned_brief_description", value)} />
          <TextArea label="Subject/Law involved" value={valueOf(metadata, "impugned_subject_law")} onChange={(value) => set("impugned_subject_law", value)} />
        </div>
      </Panel>

      <Panel title="Interlocutory Application Details">
        <div className="phhc-grid phhc-grid-6">
          <Field label="Doc No./Year" value={valueOf(metadata, "lower_court_document_no")} onChange={(value) => set("lower_court_document_no", value)} />
          <Field label="Document Year" value={valueOf(metadata, "lower_court_document_year")} onChange={(value) => set("lower_court_document_year", value)} />
          <Field label="IA No." value={valueOf(metadata, "lower_court_ia_no")} onChange={(value) => set("lower_court_ia_no", value)} />
          <Field label="Particular" value={valueOf(metadata, "lower_court_ia_particular")} onChange={(value) => set("lower_court_ia_particular", value)} />
          <Field label="Amount" value={valueOf(metadata, "lower_court_ia_amount")} onChange={(value) => set("lower_court_ia_amount", value)} />
          <Field label="Filed By" value={valueOf(metadata, "lower_court_ia_filed_by")} onChange={(value) => set("lower_court_ia_filed_by", value)} />
          <SelectField label="IA Status" value={valueOf(metadata, "lower_court_ia_status")} onChange={(value) => set("lower_court_ia_status", value)} options={["Pending", "Allowed", "Dismissed", "Disposed"]} />
          <Field label="Remark" value={valueOf(metadata, "lower_court_ia_remark")} onChange={(value) => set("lower_court_ia_remark", value)} />
        </div>
      </Panel>
    </>
  );
}
