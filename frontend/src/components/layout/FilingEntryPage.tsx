import { useState } from "react";
import { fetchEFilingData } from "../../services/efilingApi";
import type { EFilingFetchResponse } from "../../types/efiling";

type Props = {
  onFetched: (data: EFilingFetchResponse) => void;
  onManualUploadSelected: (file: File) => void;
  uploading?: boolean;
};

export default function FilingEntryPage({
  onFetched,
  onManualUploadSelected,
  uploading = false,
}: Props) {
  const [provisionalNo, setProvisionalNo] = useState("");
  const [provisionalYear, setProvisionalYear] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFetch = async () => {
    if (!provisionalNo.trim() || !provisionalYear.trim()) {
      alert("Enter provisional number and provisional year.");
      return;
    }

    setLoading(true);
    try {
      const data = await fetchEFilingData({
        provisional_no: provisionalNo.trim(),
        provisional_year: provisionalYear.trim(),
      });
      onFetched(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="entry-page">
      <div className="entry-topbar">
        <div className="brand">PHHC</div>
        <div className="top-search">Enter keyword</div>
      </div>

      <div className="entry-shell">
        <aside className="sidebar">
          <div className="sidebar-item active">High Court</div>
          <div className="sidebar-sub active">E-Filing Consume</div>
          <div className="sidebar-sub active-light">Filing Consume</div>
          <div className="sidebar-sub">Registration</div>
          <div className="sidebar-sub">Scrutiny</div>
        </aside>

        <main className="entry-main">
          <div className="entry-header">
            <div>
              <h1>E-Filing Application Form</h1>
              <p>Fetch an e-filing record or use manual PDF upload for local testing.</p>
            </div>

            <div className="entry-actions">
              <button className="btn" type="button">Back to Dashboard</button>
              <button className="btn" type="button">Consume Report</button>
            </div>
          </div>

          <section className="entry-card">
            <label className="field">
              <span>Provisional No.</span>
              <input
                value={provisionalNo}
                onChange={(event) => setProvisionalNo(event.target.value)}
                placeholder="Enter Provisional No."
              />
            </label>

            <label className="field">
              <span>Provisional Year</span>
              <input
                value={provisionalYear}
                onChange={(event) => setProvisionalYear(event.target.value)}
                placeholder="YYYY"
              />
            </label>

            <button className="btn btn-primary entry-fetch" type="button" onClick={handleFetch} disabled={loading}>
              {loading ? "Fetching..." : "Fetch E-Filing Data"}
            </button>
          </section>

          <section className="entry-card entry-upload-card">
            <h3>Manual PDF Upload</h3>
            <p>Use the current local test upload/process/extraction pipeline.</p>
            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => {
                const selected = event.target.files?.[0];
                if (selected) onManualUploadSelected(selected);
              }}
            />
            {uploading && <div className="muted">Uploading...</div>}
          </section>
        </main>
      </div>
    </div>
  );
}
