import { api } from "./api";
import type {
  FilingSubmissionPreviewResponse,
  DryRunSubmissionResponse,
} from "../types/filingSubmission";

export async function getSubmissionPreview(documentId: number): Promise<FilingSubmissionPreviewResponse> {
  const response = await api.get(`/api/v1/filing-submission/${documentId}/preview`);
  return response.data;
}

export async function prepareSubmission(documentId: number): Promise<FilingSubmissionPreviewResponse> {
  const response = await api.post(`/api/v1/filing-submission/${documentId}/prepare`, {
    dry_run: true,
  });
  return response.data;
}

export async function dryRunSubmission(documentId: number): Promise<DryRunSubmissionResponse> {
  const response = await api.post(`/api/v1/filing-submission/${documentId}/dry-run`, {
    dry_run: true,
  });
  return response.data;
}
