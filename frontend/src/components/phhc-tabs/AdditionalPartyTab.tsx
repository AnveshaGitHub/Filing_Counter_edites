import type { ExtraPartyItem, FilingFullMetadata } from "../../types/filingFullMetadata";
import { Field, Panel, SearchStrip, SelectField } from "./shared";

type Props = {
  metadata: FilingFullMetadata;
  set: (key: string, value: unknown) => void;
};

export default function AdditionalPartyTab({ metadata, set }: Props) {
  const parties = metadata.extra_parties || [];

  const updateParty = (index: number, key: keyof ExtraPartyItem, value: string) => {
    const next = [...parties];
    next[index] = { ...(next[index] || {}), [key]: value };
    set("extra_parties", next);
  };

  const removeParty = (index: number) => {
    set("extra_parties", parties.filter((_, rowIndex) => rowIndex !== index));
  };

  const addParty = () => {
    set("extra_parties", [
      ...parties,
      {
        pet_res: "",
        party_no: "",
        ind_dept: "Individual",
        name: "",
        relation: "",
        father_husband_name: "",
        sex: "",
        age: "",
        occupation_department: "",
        address: "",
        place_city: "",
        state: "MADHYA PRADESH",
        district: "",
        pin: "",
        phone_mobile: "",
        email_id: "",
        status: "Pending",
      },
    ]);
  };

  return (
    <>
      <SearchStrip metadata={metadata} set={set} />

      <Panel title="Existing Petitioner / Respondent Parties">
        <div className="phhc-list-row">
          <div>
            <strong>Petitioner</strong>
            <div>{typeof metadata.petitioner_display_name === "string" ? metadata.petitioner_display_name : "-"}</div>
          </div>
          <div>
            <strong>Respondent</strong>
            <div>{typeof metadata.respondent_display_name === "string" ? metadata.respondent_display_name : "-"}</div>
          </div>
        </div>
      </Panel>

      <Panel title="Memo of Parties / Additional Party">
        <button type="button" className="phhc-primary-btn" onClick={addParty}>
          Add Party
        </button>

        {parties.length === 0 && <div className="phhc-info">Load a case or add a party to start memo of parties.</div>}

        {parties.map((party, index) => (
          <div className="phhc-sub-card" key={`party-${index}`}>
            <div className="phhc-sub-card-head">
              <div className="phhc-sub-title">Party {index + 1}</div>
              <button type="button" className="phhc-secondary-btn" onClick={() => removeParty(index)}>
                Remove
              </button>
            </div>
            <div className="phhc-grid phhc-grid-4">
              <SelectField label="Pet/Res." value={party.pet_res} onChange={(value) => updateParty(index, "pet_res", value)} options={["Petitioner", "Respondent"]} />
              <Field label="Party No." value={party.party_no} onChange={(value) => updateParty(index, "party_no", value)} />
              <SelectField label="Ind./Dept." value={party.ind_dept} onChange={(value) => updateParty(index, "ind_dept", value)} options={["Individual", "State Department", "Central Department", "Other Organization"]} />
              <Field label="Name" value={party.name} onChange={(value) => updateParty(index, "name", value)} />
              <SelectField label="Relation" value={party.relation} onChange={(value) => updateParty(index, "relation", value)} options={["S/o", "W/o", "D/o", "Father", "Mother", "Husband"]} />
              <Field label="Father/Husband Name" value={party.father_husband_name} onChange={(value) => updateParty(index, "father_husband_name", value)} />
              <SelectField label="Sex" value={party.sex} onChange={(value) => updateParty(index, "sex", value)} options={["Male", "Female", "Other"]} />
              <Field label="Age" value={party.age} onChange={(value) => updateParty(index, "age", value)} />
              <Field label="Occupation/Dept." value={party.occupation_department} onChange={(value) => updateParty(index, "occupation_department", value)} />
              <Field label="Address" value={party.address} onChange={(value) => updateParty(index, "address", value)} />
              <Field label="Place/City" value={party.place_city} onChange={(value) => updateParty(index, "place_city", value)} />
              <Field label="State" value={party.state} onChange={(value) => updateParty(index, "state", value)} />
              <Field label="District" value={party.district} onChange={(value) => updateParty(index, "district", value)} />
              <Field label="Pin" value={party.pin} onChange={(value) => updateParty(index, "pin", value)} />
              <Field label="Phone/Mobile" value={party.phone_mobile} onChange={(value) => updateParty(index, "phone_mobile", value)} />
              <Field label="Email Id" value={party.email_id} onChange={(value) => updateParty(index, "email_id", value)} />
              <SelectField label="Status" value={party.status} onChange={(value) => updateParty(index, "status", value)} options={["Pending", "Accepted", "Rejected"]} />
            </div>
          </div>
        ))}
      </Panel>
    </>
  );
}
