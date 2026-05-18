import type { ExtractionResponse } from "../types/filingExtraction";
import type { CreateReviewSessionRequest } from "../types/filingReview";
import type { FilingFormState } from "./filingExtractionMapper";

export function filingFormToReviewPayload(
  extraction: ExtractionResponse,
  form: FilingFormState,
  reviewedBy?: string
): CreateReviewSessionRequest {
  const fields = extraction.fields.map((f) => {
    let reviewedValue: string | null = f.value || null;

    switch (f.field_key) {
      case "case_type":
        reviewedValue = form.caseType || null;
        break;
      case "list_type":
        reviewedValue = form.listType || null;
        break;
      case "with_application":
        reviewedValue = form.withApplication ? "true" : null;
        break;
      case "petitioner_name":
        reviewedValue = form.petitionerName || null;
        break;
      case "petitioner_party_type":
        reviewedValue = form.petitionerType || null;
        break;
      case "hide_party_petitioner":
        reviewedValue = form.hidePartyPetitioner ? "true" : null;
        break;
      case "differently_abled_petitioner":
        reviewedValue = form.differentlyAbledPetitioner ? "true" : null;
        break;
      case "respondent_name":
        reviewedValue = form.respondentName || null;
        break;
      case "respondent_party_type":
        reviewedValue = form.respondentType || null;
        break;
      case "hide_party_respondent":
        reviewedValue = form.hidePartyRespondent ? "true" : null;
        break;
      case "differently_abled_respondent":
        reviewedValue = form.differentlyAbledRespondent ? "true" : null;
        break;
      case "advocate_name":
        reviewedValue = form.advocates?.[0]?.name || null;
        break;
      case "advocate_enrol_no":
        reviewedValue = form.advocates?.[0]?.enrolNo || null;
        break;
      case "advocate_enrol_year":
        reviewedValue = form.advocates?.[0]?.enrolYear || null;
        break;
      case "advocate_mobile":
        reviewedValue = form.advocates?.[0]?.mobile || null;
        break;
      case "advocate_remark":
        reviewedValue = form.advocates?.[0]?.remark || null;
        break;
    }

    return {
      field_key: f.field_key,
      field_label: f.field_label,
      system_value: f.value || null,
      reviewed_value: reviewedValue,
      confidence: f.confidence,
      action_taken: (f.value || "") === (reviewedValue || "") ? "accepted" : "edited",
      evidence_text: f.evidence?.text || null,
      source_type: f.evidence?.source_type || null
    };
  });

  const ensureField = (fieldKey: string, fieldLabel: string, reviewedValue: string | null) => {
    if (fields.some((f) => f.field_key === fieldKey)) return;
    fields.push({
      field_key: fieldKey,
      field_label: fieldLabel,
      system_value: null,
      reviewed_value: reviewedValue,
      confidence: 0,
      action_taken: reviewedValue ? "edited" : "accepted",
      evidence_text: null,
      source_type: null
    });
  };

  ensureField("case_type", "Case Type", form.caseType || null);
  ensureField("list_type", "List Type", form.listType || null);

  return {
    extraction_job_id: extraction.job.extraction_job_id,
    reviewed_by: reviewedBy || null,
    status: "reviewed",
    submit_ready: true,
    notes: null,
    fields
  };
}
