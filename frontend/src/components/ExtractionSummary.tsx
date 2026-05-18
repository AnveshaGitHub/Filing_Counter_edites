import type { ExtractionResponse } from "../types/filingExtraction";
import StatusPill from "./StatusPill";

type Props = {
  extraction: ExtractionResponse | null;
};

export default function ExtractionSummary({ extraction }: Props) {
  if (!extraction) return null;

  const tone =
    extraction.job.status === "completed"
      ? "good"
      : extraction.job.status === "needs_review"
      ? "warn"
      : "neutral";

  return (
    <div className="summary-grid">
      <div>
        <strong>Job ID</strong>
        <div>{extraction.job.extraction_job_id}</div>
      </div>
      <div>
        <strong>Status</strong>
        <div>
          <StatusPill label={extraction.job.status} tone={tone} />
        </div>
      </div>
      <div>
        <strong>Extractor Version</strong>
        <div>{extraction.job.extractor_version}</div>
      </div>
      <div>
        <strong>Overall Confidence</strong>
        <div>{extraction.job.overall_confidence ?? 0}</div>
      </div>
      <div>
        <strong>Confirmed</strong>
        <div>{extraction.confirmed_count}</div>
      </div>
      <div>
        <strong>Suggested</strong>
        <div>{extraction.suggested_count}</div>
      </div>
      <div>
        <strong>Missing</strong>
        <div>{extraction.missing_count}</div>
      </div>
      <div>
        <strong>Needs Review</strong>
        <div>{String(extraction.job.needs_review)}</div>
      </div>
    </div>
  );
}
