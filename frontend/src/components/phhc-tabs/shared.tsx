import type { ReactNode } from "react";

import type { FilingFullMetadata } from "../../types/filingFullMetadata";

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="phhc-panel">
      <div className="phhc-panel-head">{title}</div>
      <div className="phhc-panel-body">{children}</div>
    </section>
  );
}

export function Field({
  label,
  value,
  onChange,
  required = false,
  placeholder,
}: {
  label: string;
  value?: string | null;
  onChange: (value: string) => void;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="phhc-field">
      <span>
        {label} {required && <b>*</b>}
      </span>
      <input value={value || ""} placeholder={placeholder || label} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  required = false,
}: {
  label: string;
  value?: string | null;
  onChange: (value: string) => void;
  options: string[];
  required?: boolean;
}) {
  return (
    <label className="phhc-field">
      <span>
        {label} {required && <b>*</b>}
      </span>
      <select value={value || ""} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function TextArea({
  label,
  value,
  onChange,
}: {
  label: string;
  value?: string | null;
  onChange: (value: string) => void;
}) {
  return (
    <label className="phhc-field phhc-wide">
      <span>{label}</span>
      <textarea value={value || ""} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

export function SearchStrip({
  metadata,
  set,
  buttonText = "Submit",
}: {
  metadata: FilingFullMetadata;
  set: (key: string, value: unknown) => void;
  buttonText?: string;
}) {
  return (
    <Panel title="Load Case">
      <div className="phhc-grid phhc-grid-4">
        <SelectField
          label="Case Type"
          value={typeof metadata.case_type === "string" ? metadata.case_type : ""}
          onChange={(value) => set("case_type", value)}
          options={["MCRC", "CRA", "CRR", "FA", "MA", "WP", "AA"]}
        />
        <Field
          label="Filing / Case / CNR / Case Diary No."
          value={typeof metadata.case_no === "string" ? metadata.case_no : ""}
          onChange={(value) => set("case_no", value)}
          placeholder="Enter Filing No., Case No., CNR No., or Case Diary No."
        />
        <Field
          label="Case Year"
          value={typeof metadata.case_year === "string" ? metadata.case_year : ""}
          onChange={(value) => set("case_year", value)}
          placeholder="YYYY"
        />
        <div className="phhc-radio-row">
          <label>
            <input type="radio" name="phhc-search-kind" defaultChecked /> Case
          </label>
          <label>
            <input type="radio" name="phhc-search-kind" /> IA
          </label>
          <button type="button" className="phhc-primary-btn">
            {buttonText}
          </button>
        </div>
      </div>
    </Panel>
  );
}
