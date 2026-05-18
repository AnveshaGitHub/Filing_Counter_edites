import { api } from "./api";
import type { ExtractionResponse } from "../types/filingExtraction";

export async function getLatestFilingExtraction(documentId: number): Promise<ExtractionResponse> {
  const response = await api.get(`/api/v1/filing-extraction/${documentId}`);
  return response.data;
}
