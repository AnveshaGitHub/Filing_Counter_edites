import { api } from "./api";
import type { MasterListResponse, LinkedMasterListResponse } from "../types/masterData";

export async function getCaseTypes(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/case-types")).data;
}

export async function getSpecialCases(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/special-cases")).data;
}

export async function getPartyNameSuffixes(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/party-name-suffixes")).data;
}

export async function getListTypes(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/list-types")).data;
}

export async function getRelations(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/relations")).data;
}

export async function getGenders(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/genders")).data;
}

export async function getStates(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/states")).data;
}

export async function getDistricts(stateCode?: string): Promise<LinkedMasterListResponse> {
  return (await api.get("/api/v1/masters/districts", { params: { state_code: stateCode } })).data;
}

export async function getTehsils(districtCode?: string): Promise<LinkedMasterListResponse> {
  return (await api.get("/api/v1/masters/tehsils", { params: { district_code: districtCode } })).data;
}

export async function getVillages(tehsilCode?: string): Promise<LinkedMasterListResponse> {
  return (await api.get("/api/v1/masters/villages", { params: { tehsil_code: tehsilCode } })).data;
}

export async function getCastes(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/castes")).data;
}

export async function getIdentityProofs(): Promise<MasterListResponse> {
  return (await api.get("/api/v1/masters/identity-proofs")).data;
}
