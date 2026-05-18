import { useCallback, useState } from "react";
import type { ExtractionResponse, ExtractionRunRequest } from "../types/filingExtraction";
import { getLatestFilingExtraction } from "../services/filingExtractionApi";
import { runTestDocumentExtraction } from "../services/testDocumentsApi";

export function useFilingExtraction(documentId?: number) {
  const [data, setData] = useState<ExtractionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLatest = useCallback(async () => {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getLatestFilingExtraction(documentId);
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to fetch extraction result");
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  const run = useCallback(
    async (
      payload: ExtractionRunRequest = {
        triggered_by: "hook_runner",
        run_async: false,
        force_recompute: true,
        form_type: "filing_registration"
      }
    ) => {
      if (!documentId) return null;
      setLoading(true);
      setError(null);
      try {
        const res = await runTestDocumentExtraction(documentId, payload);
        setData(res);
        return res;
      } catch (err: any) {
        setError(err?.response?.data?.detail || "Failed to run extraction");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [documentId]
  );

  return {
    data,
    loading,
    error,
    fetchLatest,
    run
  };
}
