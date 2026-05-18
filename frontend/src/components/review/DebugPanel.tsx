import JsonBlock from "../JsonBlock";
import type { ExtractionResponse } from "../../types/filingExtraction";
import type { ReviewSessionResponse } from "../../types/filingReview";
import type { FilingPayloadResponse } from "../../types/filingPayload";

type Props = {
  extraction: ExtractionResponse | null;
  review: ReviewSessionResponse | null;
  payloadPreview: FilingPayloadResponse | null;
  shown: boolean;
};

export default function DebugPanel({ extraction, review, payloadPreview, shown }: Props) {
  if (!shown) {
    return null;
  }

  return (
    <div className="debug-grid">
      <div>
        <h4>Grouped Extraction</h4>
        {extraction?.grouped ? <JsonBlock value={extraction.grouped} /> : <div>No grouped extraction yet.</div>}
      </div>
      <div>
        <h4>Latest Review Session</h4>
        {review ? <JsonBlock value={review} /> : <div>No review loaded yet.</div>}
      </div>
      <div>
        <h4>Payload Preview</h4>
        {payloadPreview ? <JsonBlock value={payloadPreview} /> : <div>No payload preview yet.</div>}
      </div>
    </div>
  );
}
