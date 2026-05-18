import { api } from "./api";
import type { EFilingFetchRequest, EFilingFetchResponse } from "../types/efiling";

export async function fetchEFilingData(
  payload: EFilingFetchRequest
): Promise<EFilingFetchResponse> {
  const response = await api.post("/api/v1/efiling/fetch", payload);
  return response.data;
}
