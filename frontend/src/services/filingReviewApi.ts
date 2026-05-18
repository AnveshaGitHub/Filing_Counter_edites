import { api } from "./api";
import type { CreateReviewSessionRequest, ReviewSessionResponse } from "../types/filingReview";

export async function createReviewSession(
  documentId: number,
  payload: CreateReviewSessionRequest
): Promise<ReviewSessionResponse> {
  const response = await api.post(`/api/v1/filing-review/${documentId}`, payload);
  return response.data;
}

export async function getLatestReviewSession(documentId: number): Promise<ReviewSessionResponse> {
  const response = await api.get(`/api/v1/filing-review/${documentId}`);
  return response.data;
}
