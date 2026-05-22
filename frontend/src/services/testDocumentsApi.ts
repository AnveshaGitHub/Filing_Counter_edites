import { api } from "./api";
import type { LocalTestDocumentResponse, ProcessTestDocumentResponse } from "../types/testDocuments";
import type { ExtractionResponse, ExtractionRunRequest } from "../types/filingExtraction";

export async function uploadTestDocument(file: File): Promise<LocalTestDocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/api/v1/test-documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });

  return response.data;
}

export async function processTestDocument(documentId: number): Promise<ProcessTestDocumentResponse> {
  const response = await api.post(`/api/v1/test-documents/${documentId}/process`);
  return response.data;
}

export async function getTestDocument(documentId: number): Promise<LocalTestDocumentResponse> {
  const response = await api.get(`/api/v1/test-documents/${documentId}`);
  return response.data;
}

export async function runTestDocumentExtraction(
  documentId: number,
  payload: ExtractionRunRequest
): Promise<ExtractionResponse> {
  const response = await api.post(`/api/v1/test-documents/${documentId}/run-extraction`, payload);
  return response.data;
}

export async function downloadTestDocumentOcrPdf(documentId: number): Promise<Blob> {
  const response = await api.get(`/api/v1/test-documents/${documentId}/ocr-pdf`, {
    responseType: "blob"
  });
  return response.data;
}

export async function downloadTestDocumentCleanOcrDebug(documentId: number): Promise<Blob> {
  const response = await api.get(`/api/v1/test-documents/${documentId}/clean-ocr-debug`, {
    responseType: "blob"
  });
  return response.data;
}

export async function downloadTestDocumentCheckpointReport(documentId: number): Promise<Blob> {
  const response = await api.get(`/api/v1/test-documents/${documentId}/checkpoint-report`, {
    responseType: "blob"
  });
  return response.data;
}
