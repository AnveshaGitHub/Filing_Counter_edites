import { api } from "./api";
import type {
  FilingFullMetadata,
  FilingFullMetadataAutofillResponse,
  FilingFullMetadataResponse,
} from "../types/filingFullMetadata";

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

export async function autofillFilingFullMetadata(
  documentId: number,
  section: "additional-parties" | "additional-advocates" | "lower-court" | "all"
): Promise<FilingFullMetadataAutofillResponse> {
  const response = await api.post(`/api/v1/filing-full-metadata/${documentId}/autofill/${section}`);
  return response.data;
}
