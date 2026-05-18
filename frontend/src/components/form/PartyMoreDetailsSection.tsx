export type MoreDetailsState = {
  nameSuffix: string;
  relation: string;
  fatherOrHusband: string;
  occupation: string;
  gender: string;
  dateOfBirth: string;
  age: string;
  country: string;
  state: string;
  district: string;
  tehsil: string;
  village: string;
  phoneMobile: string;
  emailId: string;
  pincode: string;
  address: string;
  caste: string;
  identityProof: string;
};

type Option = {
  code: string;
  label: string;
};

type Props = {
  values: MoreDetailsState;
  onChange: (patch: Partial<MoreDetailsState>) => void;
  suffixOptions: Option[];
  relationOptions: Option[];
  genderOptions: Option[];
  stateOptions: Option[];
  districtOptions: Option[];
  tehsilOptions: Option[];
  villageOptions: Option[];
  casteOptions: Option[];
  identityProofOptions: Option[];
  expanded: boolean;
};

export default function PartyMoreDetailsSection({
  values,
  onChange,
  suffixOptions,
  relationOptions,
  genderOptions,
  stateOptions,
  districtOptions,
  tehsilOptions,
  villageOptions,
  casteOptions,
  identityProofOptions,
  expanded,
}: Props) {
  if (!expanded) return null;

  return (
    <div className="more-details-grid" data-suffix-count={suffixOptions.length}>
      <label className="field">
        <span>Relation</span>
        <select value={values.relation} onChange={(e) => onChange({ relation: e.target.value })}>
          <option value="">Select Relation</option>
          {relationOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Father/Husband</span>
        <input
          value={values.fatherOrHusband}
          onChange={(e) => onChange({ fatherOrHusband: e.target.value })}
          placeholder="Father / Husband"
        />
      </label>

      <label className="field">
        <span>Occupation</span>
        <input
          value={values.occupation}
          onChange={(e) => onChange({ occupation: e.target.value })}
          placeholder="Occupation"
        />
      </label>

      <label className="field">
        <span>Gender</span>
        <select value={values.gender} onChange={(e) => onChange({ gender: e.target.value })}>
          <option value="">Select Gender</option>
          {genderOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Date of Birth</span>
        <input
          value={values.dateOfBirth}
          onChange={(e) => onChange({ dateOfBirth: e.target.value })}
          placeholder="DD-MM-YYYY"
        />
      </label>

      <label className="field">
        <span>Age</span>
        <input
          value={values.age}
          onChange={(e) => onChange({ age: e.target.value })}
          placeholder="Age"
        />
      </label>

      <label className="field">
        <span>Country</span>
        <input
          value={values.country}
          onChange={(e) => onChange({ country: e.target.value })}
          placeholder="India"
        />
      </label>

      <label className="field">
        <span>State</span>
        <select value={values.state} onChange={(e) => onChange({ state: e.target.value })}>
          <option value="">Select State</option>
          {stateOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>District</span>
        <select value={values.district} onChange={(e) => onChange({ district: e.target.value })}>
          <option value="">Select District</option>
          {districtOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Tehsil</span>
        <select value={values.tehsil} onChange={(e) => onChange({ tehsil: e.target.value })}>
          <option value="">Select Tehsil</option>
          {tehsilOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Village</span>
        <select value={values.village} onChange={(e) => onChange({ village: e.target.value })}>
          <option value="">Select Village</option>
          {villageOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Phone/Mobile</span>
        <input
          value={values.phoneMobile}
          onChange={(e) => onChange({ phoneMobile: e.target.value })}
          placeholder="Phone / Mobile"
        />
      </label>

      <label className="field">
        <span>Email Id</span>
        <input
          value={values.emailId}
          onChange={(e) => onChange({ emailId: e.target.value })}
          placeholder="Email Id"
        />
      </label>

      <label className="field">
        <span>Pincode</span>
        <input
          value={values.pincode}
          onChange={(e) => onChange({ pincode: e.target.value })}
          placeholder="6 digit pincode"
        />
      </label>

      <label className="field field--wide">
        <span>Address</span>
        <input
          value={values.address}
          onChange={(e) => onChange({ address: e.target.value })}
          placeholder="Address"
        />
      </label>

      <label className="field">
        <span>Caste</span>
        <select value={values.caste} onChange={(e) => onChange({ caste: e.target.value })}>
          <option value="">Select Caste</option>
          {casteOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Identity Proof</span>
        <select value={values.identityProof} onChange={(e) => onChange({ identityProof: e.target.value })}>
          <option value="">Select Identity Proof</option>
          {identityProofOptions.map((x) => (
            <option key={x.code} value={x.code}>{x.label}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
