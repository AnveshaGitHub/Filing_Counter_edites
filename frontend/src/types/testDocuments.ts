export interface LocalTestDocumentResponse {
  id: number;
  original_filename: string;
  stored_path: string;
  status: string;
  source: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProcessTestDocumentResponse {
  document_id: number;
  status: string;
  pages: number;
  chunks: number;
  pages_with_embedded_text?: number;
  pages_with_ocr_fallback?: number;
}
