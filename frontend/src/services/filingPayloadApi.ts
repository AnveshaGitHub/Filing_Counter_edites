import { api } from "./api";
import type { FilingPayloadResponse } from "../types/filingPayload";

export async function getFilingPayload(documentId: number): Promise<FilingPayloadResponse> {
  const response = await api.get(`/api/v1/filing-payload/${documentId}`);
  return response.data;
}
