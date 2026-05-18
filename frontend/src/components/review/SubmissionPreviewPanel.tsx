import type {
  FilingSubmissionPreviewResponse,
  DryRunSubmissionResponse,
} from "../../types/filingSubmission";

type Props = {
  preview: FilingSubmissionPreviewResponse | null;
  dryRunResult: DryRunSubmissionResponse | null;
};

export default function SubmissionPreviewPanel({ preview, dryRunResult }: Props) {
  return (
    <div className="submission-panel">
      {!preview ? (
        <div>No submission preview yet.</div>
      ) : (
        <>
          <div className="submission-badges">
            <span className={`status-pill ${preview.ready_for_submit ? "status-pill--good" : "status-pill--warn"}`}>
              {preview.ready_for_submit ? "Ready for Submit" : "Needs Fixes"}
            </span>
            <span className="status-pill status-pill--neutral">{preview.target_system}</span>
            <span className="status-pill status-pill--neutral">{preview.dry_run ? "Dry Run" : "Real Mode"}</span>
          </div>

          <pre className="json-block">{JSON.stringify(preview.payload, null, 2)}</pre>

          <div className="submission-issues">
            <strong>Validation Issues</strong>
            {preview.validation_issues.length ? (
              <ul>
                {preview.validation_issues.map((issue, index) => (
                  <li key={`${issue.field_key}-${index}`}>
                    {issue.field_key}: {issue.message}
                  </li>
                ))}
              </ul>
            ) : (
              <div>No validation issues.</div>
            )}
          </div>
        </>
      )}

      {dryRunResult && (
        <div className="submission-issues">
          <strong>Dry Run Result</strong>
          <pre className="json-block">{JSON.stringify(dryRunResult, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
