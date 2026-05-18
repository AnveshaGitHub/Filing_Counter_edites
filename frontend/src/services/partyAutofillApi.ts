import { api } from "./api";
import type { PartyAutofillResponse } from "../types/partyAutofill";

export async function autofillPetitionerDetails(documentId: number): Promise<PartyAutofillResponse> {
  const response = await api.post(`/api/v1/party-autofill/${documentId}/petitioner`);
  return response.data;
}

export async function autofillRespondentDetails(documentId: number): Promise<PartyAutofillResponse> {
  const response = await api.post(`/api/v1/party-autofill/${documentId}/respondent`);
  return response.data;
}
