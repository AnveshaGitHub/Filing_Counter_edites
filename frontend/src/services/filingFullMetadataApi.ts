import { api } from "./api";
import type { FilingFullMetadata, FilingFullMetadataResponse } from "../types/filingFullMetadata";

export async function getFilingFullMetadata(documentId: number): Promise<FilingFullMetadataResponse> {
  const response = await api.get(`/api/v1/filing-full-metadata/${documentId}`);
  return response.data;
}

export async function saveFilingFullMetadata(
  documentId: number,
  metadata: FilingFullMetadata
): Promise<FilingFullMetadataResponse> {
  const response = await api.post(`/api/v1/filing-full-metadata/${documentId}`, metadata);
  return response.data;
}
