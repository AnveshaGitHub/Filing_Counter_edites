import type { FilingPayloadResponse } from "../types/filingPayload";

export function payloadIssuesByField(payload: FilingPayloadResponse): Record<string, string[]> {
  return payload.issues.reduce((acc, issue) => {
    if (!acc[issue.field_key]) acc[issue.field_key] = [];
    acc[issue.field_key].push(issue.message);
    return acc;
  }, {} as Record<string, string[]>);
}
