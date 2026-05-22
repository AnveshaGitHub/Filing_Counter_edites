import type { ExtraAdvocateItem, FilingFullMetadata } from "../../types/filingFullMetadata";
import { Field, Panel, SearchStrip, SelectField } from "./shared";

function AdvocateRows({
  title,
  rows,
  setRows,
}: {
  title: string;
  rows: ExtraAdvocateItem[];
  setRows: (rows: ExtraAdvocateItem[]) => void;
}) {
  const update = (index: number, key: keyof ExtraAdvocateItem, value: string) => {
    const next = [...rows];
    next[index] = { ...(next[index] || {}), [key]: value };
    setRows(next);
  };

  const add = () => {
    setRows([
      ...rows,
      {
        advocate_no: "",
        advocate_year: "",
        advocate_name: "",
        mobile: "",
        email: "",
        party_no: "",
        type: "None",
        if_ag: "No",
      },
    ]);
  };

  const remove = (index: number) => {
    setRows(rows.filter((_, rowIndex) => rowIndex !== index));
  };

  return (
    <div className="phhc-sub-card">
      <div className="phhc-sub-card-head">
        <div className="phhc-sub-title">{title}</div>
        <button type="button" className="phhc-primary-btn" onClick={add}>
          New
        </button>
      </div>

      {rows.length === 0 && <div className="phhc-info">No advocate rows added.</div>}

      {rows.map((row, index) => (
        <div className="phhc-row-block" key={`${title}-${index}`}>
          <div className="phhc-grid phhc-grid-8">
            <Field label="Advocate No." value={row.advocate_no} onChange={(value) => update(index, "advocate_no", value)} />
            <Field label="Advocate Year" value={row.advocate_year} onChange={(value) => update(index, "advocate_year", value)} />
            <Field label="Advocate Name" value={row.advocate_name} onChange={(value) => update(index, "advocate_name", value)} />
            <Field label="Mobile" value={row.mobile} onChange={(value) => update(index, "mobile", value)} />
            <Field label="Email" value={row.email} onChange={(value) => update(index, "email", value)} />
            <Field label="Party No." value={row.party_no} onChange={(value) => update(index, "party_no", value)} />
            <SelectField label="Type" value={row.type} onChange={(value) => update(index, "type", value)} options={["None", "Petitioner", "Respondent", "State", "Private"]} />
            <SelectField label="If AG" value={row.if_ag} onChange={(value) => update(index, "if_ag", value)} options={["No", "Yes"]} />
          </div>
          <button type="button" className="phhc-secondary-btn" onClick={() => remove(index)}>
            Remove
          </button>
        </div>
      ))}
    </div>
  );
}

export default function AdditionalAdvocateTab({
  documentId,
  metadata,
  set,
  onAutofill,
  autofilling = false,
}: {
  documentId?: number;
  metadata: FilingFullMetadata;
  set: (key: string, value: unknown) => void;
  onAutofill: (section: "additional-advocates") => Promise<void>;
  autofilling?: boolean;
}) {
  return (
    <>
      <SearchStrip metadata={metadata} set={set} />

      <Panel title="Advocate Details">
        <div className="button-row">
          <button
            type="button"
            className="phhc-primary-btn"
            disabled={!documentId || autofilling}
            onClick={() => onAutofill("additional-advocates")}
          >
            {autofilling ? "Autofilling..." : "Autofill Advocate Details"}
          </button>
        </div>
        <AdvocateRows
          title="Petitioner"
          rows={metadata.petitioner_extra_advocates || []}
          setRows={(rows) => set("petitioner_extra_advocates", rows)}
        />
        <AdvocateRows
          title="Respondent"
          rows={metadata.respondent_extra_advocates || []}
          setRows={(rows) => set("respondent_extra_advocates", rows)}
        />
      </Panel>
    </>
  );
}
