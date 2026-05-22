import { useEffect, useMemo, useState } from "react";
import "./styles.css";

import SectionCard from "./components/SectionCard";
import StatusPill from "./components/StatusPill";
import ExtractionSummary from "./components/ExtractionSummary";
import PageHeader from "./components/layout/PageHeader";
import FilingEntryPage from "./components/layout/FilingEntryPage";
import FilingWorkspace from "./components/layout/FilingWorkspace";
import SubmissionPreviewPanel from "./components/review/SubmissionPreviewPanel";
import DebugPanel from "./components/review/DebugPanel";
import SuggestionChips from "./components/SuggestionChips";
import PartyMoreDetailsSection, { type MoreDetailsState } from "./components/form/PartyMoreDetailsSection";
import PhhcTabs from "./components/phhc-tabs/PhhcTabs";

import {
  getCaseTypes,
  getPartyNameSuffixes,
  getSpecialCases,
  getListTypes,
  getRelations,
  getGenders,
  getStates,
  getDistricts,
  getTehsils,
  getVillages,
  getCastes,
  getIdentityProofs,
} from "./services/masterDataApi";
import { autofillPetitionerDetails, autofillRespondentDetails } from "./services/partyAutofillApi";
import { getHealth } from "./services/healthApi";
import {
  uploadTestDocument,
  processTestDocument,
  getTestDocument,
  runTestDocumentExtraction,
  downloadTestDocumentOcrPdf,
  downloadTestDocumentCleanOcrDebug,
  downloadTestDocumentCheckpointReport,
} from "./services/testDocumentsApi";
import { createReviewSession, getLatestReviewSession } from "./services/filingReviewApi";
import { getFilingPayload } from "./services/filingPayloadApi";
import { getSubmissionPreview, prepareSubmission, dryRunSubmission } from "./services/filingSubmissionApi";
import {
  autofillFilingFullMetadata,
  getFilingFullMetadata,
  saveFilingFullMetadata,
} from "./services/filingFullMetadataApi";

import type { LocalTestDocumentResponse, ProcessTestDocumentResponse } from "./types/testDocuments";
import type { ExtractionResponse, FieldResult } from "./types/filingExtraction";
import type { ReviewSessionResponse } from "./types/filingReview";
import type { FilingPayloadResponse } from "./types/filingPayload";
import type {
  FilingSubmissionPreviewResponse,
  DryRunSubmissionResponse,
} from "./types/filingSubmission";
import type { EFilingFetchResponse } from "./types/efiling";
import type { MasterOption } from "./types/masterData";
import type { PartyAutofillResponse } from "./types/partyAutofill";
import type { FilingFullMetadata } from "./types/filingFullMetadata";

import {
  applyConfirmedExtractionToForm,
  emptyFormState,
  type FilingFormState,
} from "./utils/filingExtractionMapper";
import { filingFormToReviewPayload } from "./utils/filingFormToReview";

function issueKeyToFormKey(fieldKey: string): string {
  const map: Record<string, string> = {
    case_type: "caseType",
    list_type: "listType",
    with_application: "withApplication",
    petitioner_party_type: "petitionerType",
    petitioner_name: "petitionerName",
    hide_party_petitioner: "hidePartyPetitioner",
    differently_abled_petitioner: "differentlyAbledPetitioner",
    respondent_party_type: "respondentType",
    respondent_name: "respondentName",
    hide_party_respondent: "hidePartyRespondent",
    differently_abled_respondent: "differentlyAbledRespondent",
    "advocates[0].adv_code": "advocates.0.advCode",
    "advocates[0].enrol_no": "advocates.0.enrolNo",
    "advocates[0].enrol_year": "advocates.0.enrolYear",
    "advocates[0].name": "advocates.0.name",
    "advocates[0].mobile": "advocates.0.mobile",
    "advocates[0].remark": "advocates.0.remark",
  };
  return map[fieldKey] || fieldKey;
}

const emptyMoreDetails: MoreDetailsState = {
  nameSuffix: "",
  relation: "",
  fatherOrHusband: "",
  occupation: "",
  gender: "",
  dateOfBirth: "",
  age: "",
  country: "India",
  state: "",
  district: "",
  tehsil: "",
  village: "",
  phoneMobile: "",
  emailId: "",
  pincode: "",
  address: "",
  caste: "",
  identityProof: "",
};

const autofillFieldMap: Record<keyof MoreDetailsState, keyof PartyAutofillResponse["data"]> = {
  nameSuffix: "name_suffix",
  relation: "relation",
  fatherOrHusband: "father_or_husband",
  occupation: "occupation",
  gender: "gender",
  dateOfBirth: "date_of_birth",
  age: "age",
  country: "country",
  state: "state",
  district: "district",
  tehsil: "tehsil",
  village: "village",
  phoneMobile: "phone_mobile",
  emailId: "email_id",
  pincode: "pincode",
  address: "address",
  caste: "caste",
  identityProof: "identity_proof",
};

function autofillWarnings(response: PartyAutofillResponse): string[] {
  return [
    ...(!response.safe_to_apply ? ["safe_to_apply=false: lower court source requires review"] : []),
    ...(response.rejected_fields || []),
    ...(response.skipped_fields || []),
  ];
}

function applyPartyAutofill(prev: MoreDetailsState, response: PartyAutofillResponse): MoreDetailsState {
  const accepted = new Set(response.accepted_fields || []);
  const next = { ...prev };

  for (const [formKey, responseKey] of Object.entries(autofillFieldMap) as [
    keyof MoreDetailsState,
    keyof PartyAutofillResponse["data"],
  ][]) {
    const value = response.data[responseKey]?.value;
    if (accepted.has(responseKey) && value) {
      next[formKey] = value;
    }
  }

  return next;
}

function applyLocationCascade(prev: MoreDetailsState, patch: Partial<MoreDetailsState>): MoreDetailsState {
  const next = { ...prev, ...patch };
  if (Object.prototype.hasOwnProperty.call(patch, "state")) {
    next.district = "";
    next.tehsil = "";
    next.village = "";
  } else if (Object.prototype.hasOwnProperty.call(patch, "district")) {
    next.tehsil = "";
    next.village = "";
  } else if (Object.prototype.hasOwnProperty.call(patch, "tehsil")) {
    next.village = "";
  }
  return next;
}

function safeDownloadName(name: string): string {
  return name.replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_");
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadJsonFile(value: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(value, null, 2)], {
    type: "application/json"
  });
  downloadBlob(blob, filename);
}

function App() {
  const [screen, setScreen] = useState<"entry" | "workspace">("entry");
  const [efilingData, setEfilingData] = useState<EFilingFetchResponse | null>(null);
  const [localPdfUrl, setLocalPdfUrl] = useState<string | null>(null);
  const [activeWorkflowTab, setActiveWorkflowTab] = useState<string>("Main Party");
  const [health, setHealth] = useState<string>("unknown");
  const [file, setFile] = useState<File | null>(null);
  const [documentInfo, setDocumentInfo] = useState<LocalTestDocumentResponse | null>(null);
  const [processInfo, setProcessInfo] = useState<ProcessTestDocumentResponse | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const [review, setReview] = useState<ReviewSessionResponse | null>(null);
  const [payloadPreview, setPayloadPreview] = useState<FilingPayloadResponse | null>(null);
  const [submissionPreview, setSubmissionPreview] = useState<FilingSubmissionPreviewResponse | null>(null);
  const [dryRunResult, setDryRunResult] = useState<DryRunSubmissionResponse | null>(null);
  const [form, setForm] = useState<FilingFormState>(emptyFormState);
  const [fullMetadata, setFullMetadata] = useState<FilingFullMetadata>({});
  const [reviewedBy, setReviewedBy] = useState<string>("manual_tester");
  const [busy, setBusy] = useState<string>("");
  const [showDebug, setShowDebug] = useState<boolean>(false);

  const [caseTypeOptions, setCaseTypeOptions] = useState<MasterOption[]>([]);
  const [specialCaseOptions, setSpecialCaseOptions] = useState<MasterOption[]>([]);
  const [partyNameSuffixOptions, setPartyNameSuffixOptions] = useState<MasterOption[]>([]);
  const [listTypeOptions, setListTypeOptions] = useState<MasterOption[]>([]);
  const [relationOptions, setRelationOptions] = useState<MasterOption[]>([]);
  const [genderOptions, setGenderOptions] = useState<MasterOption[]>([]);
  const [stateOptions, setStateOptions] = useState<MasterOption[]>([]);
  const [casteOptions, setCasteOptions] = useState<MasterOption[]>([]);
  const [identityProofOptions, setIdentityProofOptions] = useState<MasterOption[]>([]);
  const [petitionerDistrictOptions, setPetitionerDistrictOptions] = useState<MasterOption[]>([]);
  const [respondentDistrictOptions, setRespondentDistrictOptions] = useState<MasterOption[]>([]);
  const [petitionerTehsilOptions, setPetitionerTehsilOptions] = useState<MasterOption[]>([]);
  const [respondentTehsilOptions, setRespondentTehsilOptions] = useState<MasterOption[]>([]);
  const [petitionerVillageOptions, setPetitionerVillageOptions] = useState<MasterOption[]>([]);
  const [respondentVillageOptions, setRespondentVillageOptions] = useState<MasterOption[]>([]);

  const [specialCase, setSpecialCase] = useState("");
  const [petitionerDetailsExpanded, setPetitionerDetailsExpanded] = useState(false);
  const [respondentDetailsExpanded, setRespondentDetailsExpanded] = useState(false);
  const [petitionerMoreDetails, setPetitionerMoreDetails] = useState<MoreDetailsState>(emptyMoreDetails);
  const [respondentMoreDetails, setRespondentMoreDetails] = useState<MoreDetailsState>(emptyMoreDetails);
  const [petitionerAutofillWarnings, setPetitionerAutofillWarnings] = useState<string[]>([]);
  const [respondentAutofillWarnings, setRespondentAutofillWarnings] = useState<string[]>([]);
  const [caseTypeDropdownOpen, setCaseTypeDropdownOpen] = useState<boolean>(false);

  const fieldMap = useMemo(() => {
    return (
      extraction?.fields?.reduce((acc, field) => {
        acc[field.field_key] = field;
        return acc;
      }, {} as Record<string, FieldResult>) || {}
    );
  }, [extraction]);

  const validationMap = useMemo(() => {
    const issues = submissionPreview?.validation_issues || [];
    const map: Record<string, string[]> = {};
    for (const issue of issues) {
      const key = issueKeyToFormKey(issue.field_key);
      if (!map[key]) map[key] = [];
      map[key].push(issue.message);
    }
    return map;
  }, [submissionPreview]);

  const filteredCaseTypeOptions = useMemo(() => {
    const q = (form.caseType || "").trim().toUpperCase();
    if (!q) return caseTypeOptions;
    return caseTypeOptions.filter((item) => {
      const code = (item.code || "").toUpperCase();
      const label = (item.label || "").toUpperCase();
      return code.includes(q) || label.includes(q);
    });
  }, [caseTypeOptions, form.caseType]);

  useEffect(() => {
    const loadMasters = async () => {
      try {
        const [caseTypes, specialCases, suffixes, listTypes, relations, genders, states, castes, identityProofs] = await Promise.all([
          getCaseTypes(),
          getSpecialCases(),
          getPartyNameSuffixes(),
          getListTypes(),
          getRelations(),
          getGenders(),
          getStates(),
          getCastes(),
          getIdentityProofs(),
        ]);
        setCaseTypeOptions(caseTypes.items);
        setSpecialCaseOptions(specialCases.items);
        setPartyNameSuffixOptions(suffixes.items);
        setListTypeOptions(listTypes.items);
        setRelationOptions(relations.items);
        setGenderOptions(genders.items);
        setStateOptions(states.items);
        setCasteOptions(castes.items);
        setIdentityProofOptions(identityProofs.items);
      } catch (error) {
        console.error("Failed to load masters", error);
      }
    };
    loadMasters();
  }, []);

  useEffect(() => {
    return () => {
      if (localPdfUrl) URL.revokeObjectURL(localPdfUrl);
    };
  }, [localPdfUrl]);

  useEffect(() => {
    if (!documentInfo?.id) {
      setFullMetadata({});
      return;
    }

    getFilingFullMetadata(documentInfo.id)
      .then((response) => setFullMetadata(response.metadata || {}))
      .catch(() => setFullMetadata({}));
  }, [documentInfo?.id]);

  useEffect(() => {
    const stateCode = petitionerMoreDetails.state || undefined;
    if (!stateCode) {
      setPetitionerDistrictOptions([]);
      return;
    }
    getDistricts(stateCode)
      .then((res) => setPetitionerDistrictOptions(res.items))
      .catch(() => setPetitionerDistrictOptions([]));
  }, [petitionerMoreDetails.state]);

  useEffect(() => {
    const districtCode = petitionerMoreDetails.district || undefined;
    if (!districtCode) {
      setPetitionerTehsilOptions([]);
      return;
    }
    getTehsils(districtCode)
      .then((res) => setPetitionerTehsilOptions(res.items))
      .catch(() => setPetitionerTehsilOptions([]));
  }, [petitionerMoreDetails.district]);

  useEffect(() => {
    const tehsilCode = petitionerMoreDetails.tehsil || undefined;
    if (!tehsilCode) {
      setPetitionerVillageOptions([]);
      return;
    }
    getVillages(tehsilCode)
      .then((res) => setPetitionerVillageOptions(res.items))
      .catch(() => setPetitionerVillageOptions([]));
  }, [petitionerMoreDetails.tehsil]);

  useEffect(() => {
    const stateCode = respondentMoreDetails.state || undefined;
    if (!stateCode) {
      setRespondentDistrictOptions([]);
      return;
    }
    getDistricts(stateCode)
      .then((res) => setRespondentDistrictOptions(res.items))
      .catch(() => setRespondentDistrictOptions([]));
  }, [respondentMoreDetails.state]);

  useEffect(() => {
    const districtCode = respondentMoreDetails.district || undefined;
    if (!districtCode) {
      setRespondentTehsilOptions([]);
      return;
    }
    getTehsils(districtCode)
      .then((res) => setRespondentTehsilOptions(res.items))
      .catch(() => setRespondentTehsilOptions([]));
  }, [respondentMoreDetails.district]);

  useEffect(() => {
    const tehsilCode = respondentMoreDetails.tehsil || undefined;
    if (!tehsilCode) {
      setRespondentVillageOptions([]);
      return;
    }
    getVillages(tehsilCode)
      .then((res) => setRespondentVillageOptions(res.items))
      .catch(() => setRespondentVillageOptions([]));
  }, [respondentMoreDetails.tehsil]);

  const handleHealth = async () => {
    setBusy("health");
    try {
      const data = await getHealth();
      setHealth(data.status);
    } catch {
      setHealth("failed");
    } finally {
      setBusy("");
    }
  };

  const resetFilingState = () => {
    setProcessInfo(null);
    setExtraction(null);
    setReview(null);
    setPayloadPreview(null);
    setSubmissionPreview(null);
    setDryRunResult(null);
    setForm(emptyFormState);
    setFullMetadata({});
    setSpecialCase("");
    setPetitionerMoreDetails(emptyMoreDetails);
    setRespondentMoreDetails(emptyMoreDetails);
    setPetitionerAutofillWarnings([]);
    setRespondentAutofillWarnings([]);
  };

  const uploadSelectedFile = async (selectedFile: File) => {
    setLocalPdfUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(selectedFile);
    });
    setBusy("upload");
    try {
      const data = await uploadTestDocument(selectedFile);
      setDocumentInfo(data);
      setEfilingData(null);
      resetFilingState();
      setScreen("workspace");
    } finally {
      setBusy("");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    await uploadSelectedFile(file);
  };

  const handleManualUploadSelected = async (selectedFile: File) => {
    setFile(selectedFile);
    await uploadSelectedFile(selectedFile);
  };

  const handleEFilingFetched = (data: EFilingFetchResponse) => {
    setEfilingData(data);
    setDocumentInfo(null);
    setFile(null);
    if (localPdfUrl) {
      URL.revokeObjectURL(localPdfUrl);
      setLocalPdfUrl(null);
    }
    resetFilingState();
    setActiveWorkflowTab("Main Party");
    setScreen("workspace");
  };

  const handleBackToSearch = () => {
    setScreen("entry");
  };

  const handleProcess = async () => {
    if (!documentInfo) return;
    setBusy("process");
    try {
      const data = await processTestDocument(documentInfo.id);
      setProcessInfo(data);
      const refreshed = await getTestDocument(documentInfo.id);
      setDocumentInfo(refreshed);
    } finally {
      setBusy("");
    }
  };

  const handleRunExtraction = async () => {
    if (!documentInfo) return;
    setBusy("extract");
    try {
      const data = await runTestDocumentExtraction(documentInfo.id, {
        triggered_by: reviewedBy,
        run_async: false,
        force_recompute: true,
        form_type: "filing_registration",
      });
      setExtraction(data);
    } finally {
      setBusy("");
    }
  };

  const handleDownloadExtractionJson = () => {
    if (!documentInfo || !extraction) return;
    const baseName = safeDownloadName(documentInfo.original_filename.replace(/\.pdf$/i, ""));
    downloadJsonFile(extraction, `${documentInfo.id}_${baseName}_extraction.json`);
  };

  const handleDownloadOcrPdf = async () => {
    if (!documentInfo) return;
    setBusy("download-ocr-pdf");
    try {
      const blob = await downloadTestDocumentOcrPdf(documentInfo.id);
      const baseName = safeDownloadName(documentInfo.original_filename.replace(/\.pdf$/i, ""));
      downloadBlob(blob, `${documentInfo.id}_${baseName}_ocr_text.pdf`);
    } finally {
      setBusy("");
    }
  };

  const handleDownloadCleanOcrDebug = async () => {
    if (!documentInfo) return;
    setBusy("download-clean-ocr-debug");
    try {
      const blob = await downloadTestDocumentCleanOcrDebug(documentInfo.id);
      const baseName = safeDownloadName(documentInfo.original_filename.replace(/\.pdf$/i, ""));
      downloadBlob(blob, `${documentInfo.id}_${baseName}_clean_ocr_debug.json`);
    } finally {
      setBusy("");
    }
  };

  const handleDownloadCheckpointReport = async () => {
    if (!documentInfo) return;
    setBusy("download-checkpoint-report");
    try {
      const blob = await downloadTestDocumentCheckpointReport(documentInfo.id);
      const baseName = safeDownloadName(documentInfo.original_filename.replace(/\.pdf$/i, ""));
      downloadBlob(blob, `${documentInfo.id}_${baseName}_checkpoint_report.pdf`);
    } finally {
      setBusy("");
    }
  };

  const handleApplyConfirmed = () => {
    if (!extraction) return;
    setForm((prev) => applyConfirmedExtractionToForm(extraction, prev));
  };

  const handleLoadReview = async () => {
    if (!documentInfo) return;
    setBusy("load-review");
    try {
      const data = await getLatestReviewSession(documentInfo.id);
      setReview(data);
    } finally {
      setBusy("");
    }
  };

  const handleSaveReview = async () => {
    if (!documentInfo || !extraction) return;
    setBusy("save-review");
    try {
      const payload = filingFormToReviewPayload(extraction, form, reviewedBy);
      const data = await createReviewSession(documentInfo.id, payload);
      setReview(data);
    } finally {
      setBusy("");
    }
  };

  const persistFullMetadata = async () => {
    if (!documentInfo) return null;
    const response = await saveFilingFullMetadata(documentInfo.id, fullMetadata);
    setFullMetadata(response.metadata || {});
    return response.metadata;
  };

  const handleSaveFullMetadata = async () => {
    if (!documentInfo) return;
    setBusy("save-full-metadata");
    try {
      await persistFullMetadata();
      alert("Full eCourt metadata saved");
    } finally {
      setBusy("");
    }
  };

  const handlePreviewPayload = async () => {
    if (!documentInfo) return;
    setBusy("payload");
    try {
      await persistFullMetadata();
      const data = await getFilingPayload(documentInfo.id);
      setPayloadPreview(data);
    } finally {
      setBusy("");
    }
  };

  const handleLoadSubmissionPreview = async () => {
    if (!documentInfo) return;
    setBusy("preview-submit");
    try {
      await persistFullMetadata();
      const data = await getSubmissionPreview(documentInfo.id);
      setSubmissionPreview(data);
    } finally {
      setBusy("");
    }
  };

  const handlePrepareSubmission = async () => {
    if (!documentInfo) return;
    if (extraction && !review) {
      alert("Please Save Review first so the latest form values are included in submission preview.");
      return;
    }
    setBusy("prepare-submit");
    try {
      await persistFullMetadata();
      const data = await prepareSubmission(documentInfo.id);
      setSubmissionPreview(data);
    } finally {
      setBusy("");
    }
  };

  const handleDryRunSubmission = async () => {
    if (!documentInfo) return;
    if (extraction && !review) {
      alert("Please Save Review first so the latest form values are included in submission preview.");
      return;
    }
    setBusy("dry-run-submit");
    try {
      await persistFullMetadata();
      const data = await dryRunSubmission(documentInfo.id);
      setDryRunResult(data);
    } finally {
      setBusy("");
    }
  };

  const handleAutofillPetitioner = async () => {
    if (!documentInfo) return;
    setBusy("autofill-petitioner");
    try {
      const response = await autofillPetitionerDetails(documentInfo.id);
      setPetitionerAutofillWarnings(autofillWarnings(response));
      setPetitionerMoreDetails((prev) => applyPartyAutofill(prev, response));
    } finally {
      setBusy("");
    }
  };

  const handleAutofillRespondent = async () => {
    if (!documentInfo) return;
    setBusy("autofill-respondent");
    try {
      const response = await autofillRespondentDetails(documentInfo.id);
      setRespondentAutofillWarnings(autofillWarnings(response));
      setRespondentMoreDetails((prev) => applyPartyAutofill(prev, response));
    } finally {
      setBusy("");
    }
  };

  const handleAutofillMetadata = async (
    section: "additional-parties" | "additional-advocates" | "lower-court"
  ) => {
    if (!documentInfo) return;
    setBusy(`autofill-${section}`);
    try {
      const response = await autofillFilingFullMetadata(documentInfo.id, section);
      setFullMetadata(response.metadata || {});
    } finally {
      setBusy("");
    }
  };

  const utilityPanel = (
    <>
      <SectionCard title="Upload PDF">
        <div className="stack">
          <input type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          <button className="btn btn-primary" onClick={handleUpload} disabled={!file || busy !== ""}>
            {busy === "upload" ? "Uploading..." : "Upload Test Document"}
          </button>
        </div>
      </SectionCard>

      <SectionCard
        title="Current Document"
        actions={documentInfo ? <StatusPill label={documentInfo.status} tone="neutral" /> : null}
      >
        {documentInfo ? (
          <div className="stack">
            <div><strong>ID:</strong> {documentInfo.id}</div>
            <div><strong>File:</strong> {documentInfo.original_filename}</div>
            <div><strong>Stored Path:</strong> {documentInfo.stored_path}</div>
            <div><strong>Notes:</strong> {documentInfo.notes || "-"}</div>
          </div>
        ) : (
          <div>No document uploaded yet.</div>
        )}
      </SectionCard>

      <SectionCard title="Processing & Extraction">
        <div className="stack">
          <div>
            <strong>Process status:</strong> {processInfo?.status || "not_started"}
          </div>
          <div>
            <strong>Pages:</strong> {processInfo?.pages ?? "-"} | <strong>Chunks:</strong> {processInfo?.chunks ?? "-"}
          </div>
          <div className="button-row">
            <button className="btn btn-primary" onClick={handleProcess} disabled={!documentInfo || busy !== ""}>
              {busy === "process" ? "Processing..." : "Process Document"}
            </button>
            <button className="btn btn-primary" onClick={handleRunExtraction} disabled={!documentInfo || busy !== ""}>
              {busy === "extract" ? "Extracting..." : "Run Extraction"}
            </button>
            <button className="btn" onClick={handleApplyConfirmed} disabled={!extraction}>
              Apply Confirmed
            </button>
            <button className="btn" onClick={handleDownloadExtractionJson} disabled={!extraction || busy !== ""}>
              Download JSON
            </button>
            <button
              className="btn"
              onClick={handleDownloadOcrPdf}
              disabled={!documentInfo || documentInfo.status !== "processed" || busy !== ""}
            >
              {busy === "download-ocr-pdf" ? "Preparing PDF..." : "Download OCR Text"}
            </button>
            <button
              className="btn"
              onClick={handleDownloadCleanOcrDebug}
              disabled={!documentInfo || documentInfo.status !== "processed" || busy !== ""}
            >
              {busy === "download-clean-ocr-debug" ? "Preparing Debug..." : "Download Clean OCR Debug"}
            </button>
            <button
              className="btn"
              onClick={handleDownloadCheckpointReport}
              disabled={!documentInfo || documentInfo.status !== "processed" || busy !== ""}
            >
              {busy === "download-checkpoint-report" ? "Preparing Report..." : "Download Checkpoint Report"}
            </button>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Extraction Summary">
        <ExtractionSummary extraction={extraction} />
        {!extraction && <div>No extraction result yet.</div>}
      </SectionCard>
    </>
  );

  if (screen === "entry") {
    return (
      <FilingEntryPage
        onFetched={handleEFilingFetched}
        onManualUploadSelected={handleManualUploadSelected}
        uploading={busy === "upload"}
      />
    );
  }

  return (
    <FilingWorkspace
      utilityPanel={utilityPanel}
      efilingData={efilingData}
      documentInfo={documentInfo}
      pdfUrl={localPdfUrl}
      activeTab={activeWorkflowTab}
      onTabChange={setActiveWorkflowTab}
      onBack={handleBackToSearch}
    >
      <div className="app-shell">
      <PageHeader health={health} busy={busy} onCheckHealth={handleHealth} />

      {activeWorkflowTab === "Main Party" ? (
        <div className="review-form-column">
          <SectionCard title="PHHC Filing Review Form">
            <PhhcTabs
              documentId={documentInfo?.id}
              metadata={fullMetadata}
              setMetadata={setFullMetadata}
              onAutofillMetadata={handleAutofillMetadata}
              autofillingSection={busy.startsWith("autofill-") ? busy.replace("autofill-", "") : ""}
              mainParty={<div className="form-grid">
              <section className="form-section field--wide">
                <h3 className="form-section__title">CaseType Bench / Case Details</h3>
                <div className="form-subgrid">
                  <label className="field">
                    <span>Case Type</span>
                    <div style={{ position: "relative" }}>
                      <input
                        value={form.caseType}
                        onFocus={() => setCaseTypeDropdownOpen(true)}
                        onClick={() => setCaseTypeDropdownOpen(true)}
                        onBlur={() => {
                          window.setTimeout(() => setCaseTypeDropdownOpen(false), 120);
                        }}
                        onChange={(e) => {
                          const raw = e.target.value || "";
                          const upper = raw.toUpperCase();
                          setForm((prev) => ({ ...prev, caseType: upper }));
                          setCaseTypeDropdownOpen(true);
                        }}
                        placeholder="Type to search (e.g. CONC, WP, CRA)"
                      />
                      {caseTypeDropdownOpen && (
                        <div
                          style={{
                            position: "absolute",
                            top: "100%",
                            left: 0,
                            right: 0,
                            maxHeight: "220px",
                            overflowY: "auto",
                            background: "#fff",
                            border: "1px solid #cbd5e1",
                            borderRadius: "8px",
                            zIndex: 30,
                            marginTop: "4px",
                          }}
                        >
                          {filteredCaseTypeOptions.length === 0 ? (
                            <button
                              type="button"
                              className="btn"
                              style={{ width: "100%", textAlign: "left", borderRadius: 0 }}
                              onMouseDown={(e) => e.preventDefault()}
                            >
                              No match
                            </button>
                          ) : (
                            filteredCaseTypeOptions.map((item) => (
                              <button
                                key={item.code}
                                type="button"
                                className="btn"
                                style={{ width: "100%", textAlign: "left", borderRadius: 0 }}
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={() => {
                                  setForm((prev) => ({ ...prev, caseType: item.code }));
                                  setCaseTypeDropdownOpen(false);
                                }}
                              >
                                {item.label}
                              </button>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                    <SuggestionChips
                      suggestions={fieldMap.case_type?.suggestions || []}
                      onPick={(value) => setForm((prev) => ({ ...prev, caseType: value }))}
                    />
                    {(validationMap.caseType || []).map((message) => (
                      <div key={message} className="field-errors">{message}</div>
                    ))}
                  </label>

                  <label className="field">
                    <span>List Type</span>
                    <select value={form.listType} onChange={(e) => setForm((prev) => ({ ...prev, listType: e.target.value }))}>
                      <option value="">Select List Type</option>
                      {listTypeOptions.map((x) => (
                        <option key={x.code} value={x.code}>{x.label}</option>
                      ))}
                    </select>
                    <SuggestionChips
                      suggestions={fieldMap.list_type?.suggestions || []}
                      onPick={(value) => setForm((prev) => ({ ...prev, listType: value }))}
                    />
                  </label>

                  <label className="field field--wide">
                    <span>Special Case</span>
                    <select value={specialCase} onChange={(e) => setSpecialCase(e.target.value)}>
                      <option value="">Select Special Case</option>
                      {specialCaseOptions.map((item) => (
                        <option key={item.code} value={item.code}>{item.label}</option>
                      ))}
                    </select>
                  </label>

                  <label className="checkbox-field field--wide">
                    <input type="checkbox" checked={form.withApplication} onChange={(e) => setForm((prev) => ({ ...prev, withApplication: e.target.checked }))} />
                    <span>With Application</span>
                  </label>
                </div>
              </section>

              <section className="form-section field--wide">
                <h3 className="form-section__title">Petitioner Individual / Department</h3>
                <div className="form-subgrid">
                  <label className="field">
                    <span>Petitioner Type</span>
                    <select value={form.petitionerType} onChange={(e) => setForm((prev) => ({ ...prev, petitionerType: e.target.value }))}>
                      <option value="">Select</option>
                      <option value="Individual">Individual</option>
                      <option value="State Department">State Department</option>
                      <option value="Other">Other</option>
                    </select>
                    <SuggestionChips
                      suggestions={fieldMap.petitioner_party_type?.suggestions || []}
                      onPick={(value) => setForm((prev) => ({ ...prev, petitionerType: value }))}
                    />
                  </label>

                  <div className="name-row field--wide">
                    <label className="field field--name">
                      <span>Name</span>
                      <input
                        value={form.petitionerName}
                        onChange={(e) => setForm((prev) => ({ ...prev, petitionerName: e.target.value }))}
                        placeholder="Name"
                      />
                    </label>

                    <label className="field field--suffix">
                      <span>&nbsp;</span>
                      <select
                        value={petitionerMoreDetails.nameSuffix}
                        onChange={(e) => setPetitionerMoreDetails((prev) => ({ ...prev, nameSuffix: e.target.value }))}
                      >
                        {partyNameSuffixOptions.map((item) => (
                          <option key={`${item.label}-pet`} value={item.code}>{item.label}</option>
                        ))}
                      </select>
                    </label>

                    <button type="button" className="btn" onClick={() => setPetitionerDetailsExpanded((v) => !v)}>
                      {petitionerDetailsExpanded ? "Hide details" : "More details"}
                    </button>

                    <button type="button" className="btn" onClick={handleAutofillPetitioner} disabled={!documentInfo || busy !== ""}>
                      {busy === "autofill-petitioner" ? "Auto Filling..." : "Auto Fill Details"}
                    </button>
                  </div>

                  <div className="field field--wide">
                    <SuggestionChips
                      suggestions={fieldMap.petitioner_name?.suggestions || []}
                      onPick={(value) => setForm((prev) => ({ ...prev, petitionerName: value }))}
                    />
                  </div>

                  <PartyMoreDetailsSection
                    expanded={petitionerDetailsExpanded}
                    values={petitionerMoreDetails}
                    onChange={(patch) => setPetitionerMoreDetails((prev) => applyLocationCascade(prev, patch))}
                    suffixOptions={partyNameSuffixOptions}
                    relationOptions={relationOptions}
                    genderOptions={genderOptions}
                    stateOptions={stateOptions}
                    districtOptions={petitionerDistrictOptions}
                    tehsilOptions={petitionerTehsilOptions}
                    villageOptions={petitionerVillageOptions}
                    casteOptions={casteOptions}
                    identityProofOptions={identityProofOptions}
                  />
                  {petitionerAutofillWarnings.length > 0 && (
                    <div className="autofill-warning field--wide">
                      <strong>Skipped/rejected autofill fields:</strong>
                      <ul>
                        {petitionerAutofillWarnings.slice(0, 10).map((item) => (
                          <li key={`pet-${item}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <label className="checkbox-field">
                    <input type="checkbox" checked={form.hidePartyPetitioner} onChange={(e) => setForm((prev) => ({ ...prev, hidePartyPetitioner: e.target.checked }))} />
                    <span>Hide Party Petitioner</span>
                  </label>

                  <label className="checkbox-field">
                    <input type="checkbox" checked={form.differentlyAbledPetitioner} onChange={(e) => setForm((prev) => ({ ...prev, differentlyAbledPetitioner: e.target.checked }))} />
                    <span>Differently Abled Petitioner</span>
                  </label>
                </div>
              </section>

              <section className="form-section field--wide">
                <h3 className="form-section__title">Respondent Individual / Department</h3>
                <div className="form-subgrid">
                  <label className="field">
                    <span>Respondent Type</span>
                    <select value={form.respondentType} onChange={(e) => setForm((prev) => ({ ...prev, respondentType: e.target.value }))}>
                      <option value="">Select</option>
                      <option value="Individual">Individual</option>
                      <option value="State Department">State Department</option>
                      <option value="Other">Other</option>
                    </select>
                    <SuggestionChips
                      suggestions={fieldMap.respondent_party_type?.suggestions || []}
                      onPick={(value) => setForm((prev) => ({ ...prev, respondentType: value }))}
                    />
                  </label>

                  <div className="name-row field--wide">
                    <label className="field field--name">
                      <span>Name</span>
                      <input
                        value={form.respondentName}
                        onChange={(e) => setForm((prev) => ({ ...prev, respondentName: e.target.value }))}
                        placeholder="Name"
                      />
                    </label>

                    <label className="field field--suffix">
                      <span>&nbsp;</span>
                      <select
                        value={respondentMoreDetails.nameSuffix}
                        onChange={(e) => setRespondentMoreDetails((prev) => ({ ...prev, nameSuffix: e.target.value }))}
                      >
                        {partyNameSuffixOptions.map((item) => (
                          <option key={`${item.label}-res`} value={item.code}>{item.label}</option>
                        ))}
                      </select>
                    </label>

                    <button type="button" className="btn" onClick={() => setRespondentDetailsExpanded((v) => !v)}>
                      {respondentDetailsExpanded ? "Hide details" : "More details"}
                    </button>

                    <button type="button" className="btn" onClick={handleAutofillRespondent} disabled={!documentInfo || busy !== ""}>
                      {busy === "autofill-respondent" ? "Auto Filling..." : "Auto Fill Details"}
                    </button>
                  </div>

                  <div className="field field--wide">
                    <SuggestionChips
                      suggestions={fieldMap.respondent_name?.suggestions || []}
                      onPick={(value) => setForm((prev) => ({ ...prev, respondentName: value }))}
                    />
                  </div>

                  <PartyMoreDetailsSection
                    expanded={respondentDetailsExpanded}
                    values={respondentMoreDetails}
                    onChange={(patch) => setRespondentMoreDetails((prev) => applyLocationCascade(prev, patch))}
                    suffixOptions={partyNameSuffixOptions}
                    relationOptions={relationOptions}
                    genderOptions={genderOptions}
                    stateOptions={stateOptions}
                    districtOptions={respondentDistrictOptions}
                    tehsilOptions={respondentTehsilOptions}
                    villageOptions={respondentVillageOptions}
                    casteOptions={casteOptions}
                    identityProofOptions={identityProofOptions}
                  />
                  {respondentAutofillWarnings.length > 0 && (
                    <div className="autofill-warning field--wide">
                      <strong>Skipped/rejected autofill fields:</strong>
                      <ul>
                        {respondentAutofillWarnings.slice(0, 10).map((item) => (
                          <li key={`res-${item}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <label className="checkbox-field">
                    <input type="checkbox" checked={form.hidePartyRespondent} onChange={(e) => setForm((prev) => ({ ...prev, hidePartyRespondent: e.target.checked }))} />
                    <span>Hide Party Respondent</span>
                  </label>

                  <label className="checkbox-field">
                    <input type="checkbox" checked={form.differentlyAbledRespondent} onChange={(e) => setForm((prev) => ({ ...prev, differentlyAbledRespondent: e.target.checked }))} />
                    <span>Differently Abled Respondent</span>
                  </label>
                </div>
              </section>

              <section className="form-section field--wide">
                <h3 className="form-section__title">Advocate</h3>
                <div className="adv-grid">
                  <input
                    placeholder="Advocate Code"
                    value={form.advocates[0].advCode}
                    onChange={(e) => setForm((prev) => ({ ...prev, advocates: [{ ...prev.advocates[0], advCode: e.target.value }, prev.advocates[1]] }))}
                  />
                  <input
                    placeholder="Enrol No"
                    value={form.advocates[0].enrolNo}
                    onChange={(e) => setForm((prev) => ({ ...prev, advocates: [{ ...prev.advocates[0], enrolNo: e.target.value }, prev.advocates[1]] }))}
                  />
                  <input
                    placeholder="Enrol Year"
                    value={form.advocates[0].enrolYear}
                    onChange={(e) => setForm((prev) => ({ ...prev, advocates: [{ ...prev.advocates[0], enrolYear: e.target.value }, prev.advocates[1]] }))}
                  />
                  <input
                    placeholder="Name"
                    value={form.advocates[0].name}
                    onChange={(e) => setForm((prev) => ({ ...prev, advocates: [{ ...prev.advocates[0], name: e.target.value }, prev.advocates[1]] }))}
                  />
                  <input
                    placeholder="Mobile"
                    value={form.advocates[0].mobile}
                    onChange={(e) => setForm((prev) => ({ ...prev, advocates: [{ ...prev.advocates[0], mobile: e.target.value }, prev.advocates[1]] }))}
                  />
                  <input
                    className="adv-remark"
                    placeholder="Remark"
                    value={form.advocates[0].remark}
                    onChange={(e) => setForm((prev) => ({ ...prev, advocates: [{ ...prev.advocates[0], remark: e.target.value }, prev.advocates[1]] }))}
                  />
                </div>
              </section>
            </div>}
              reviewActions={
                <div className="review-actions-card phhc-main-review-actions">
                  <label className="field bottom-action-field">
                    <span>Reviewed By</span>
                    <input value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} />
                  </label>
                  <div className="review-action-buttons">
                    <button className="btn" onClick={handleSaveReview} disabled={!extraction || busy !== ""}>
                      {busy === "save-review" ? "Saving..." : "Save Review"}
                    </button>
                    <button className="btn" onClick={handleLoadReview} disabled={!documentInfo || busy !== ""}>
                      {busy === "load-review" ? "Loading..." : "Load Review"}
                    </button>
                    <button className="btn" onClick={handlePreviewPayload} disabled={!documentInfo || busy !== ""}>
                      {busy === "payload" ? "Loading..." : "Preview Payload"}
                    </button>
                    <button className="btn" onClick={handleSaveFullMetadata} disabled={!documentInfo || busy !== ""}>
                      {busy === "save-full-metadata" ? "Saving..." : "Save Full Metadata"}
                    </button>
                    <button className="btn" onClick={handleLoadSubmissionPreview} disabled={!documentInfo || busy !== ""}>
                      {busy === "preview-submit" ? "Loading..." : "Submission Preview"}
                    </button>
                    <button className="btn" onClick={handlePrepareSubmission} disabled={!documentInfo || busy !== ""}>
                      {busy === "prepare-submit" ? "Preparing..." : "Prepare Submission Payload"}
                    </button>
                    <button className="btn btn-primary" onClick={handleDryRunSubmission} disabled={!documentInfo || busy !== ""}>
                      {busy === "dry-run-submit" ? "Running..." : "Dry Run Submission"}
                    </button>
                  </div>
                  <div className="submission-note">
                    Save Review before preparing submission to include latest manual edits.
                  </div>
                  <div className="button-row">
                    <button className="btn" onClick={() => setShowDebug((value) => !value)}>
                      {showDebug ? "Hide Debug Panel" : "Show Debug Panel"}
                    </button>
                  </div>
                </div>
              }
            />
          </SectionCard>

          <SectionCard title="Submission">
            <SubmissionPreviewPanel preview={submissionPreview} dryRunResult={dryRunResult} />
          </SectionCard>

          <SectionCard title="Debug Panel" actions={<StatusPill label={showDebug ? "visible" : "hidden"} tone="neutral" />}>
            <DebugPanel extraction={extraction} review={review} payloadPreview={payloadPreview} shown={showDebug} />
          </SectionCard>
          </div>
      ) : (
        <SectionCard title={activeWorkflowTab}>
          <div className="placeholder-panel">
            {activeWorkflowTab} workflow will be connected in the next phase. Main Party remains active now.
          </div>
        </SectionCard>
      )}
      </div>
    </FilingWorkspace>
  );
}

export default App;
