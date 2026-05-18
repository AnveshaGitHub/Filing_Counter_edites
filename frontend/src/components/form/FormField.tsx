import SuggestionChips from "../SuggestionChips";
import type { FieldCandidate } from "../../types/filingExtraction";
import type { FormFieldSchema } from "../../config/filingFormSchema";

type Props = {
  schema: FormFieldSchema;
  value: string | boolean;
  suggestions?: FieldCandidate[];
  validationMessages?: string[];
  onChange: (value: string | boolean) => void;
  onPickSuggestion: (value: string) => void;
};

export default function FormField({
  schema,
  value,
  suggestions = [],
  validationMessages = [],
  onChange,
  onPickSuggestion,
}: Props) {
  const fieldClass = schema.fullWidth ? "field field--wide" : "field";

  if (schema.control === "checkbox") {
    return (
      <label className={`${fieldClass} checkbox-field`}>
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span>{schema.label}</span>
      </label>
    );
  }

  if (schema.control === "select") {
    const placeholder = schema.key === "caseType" ? "Select Case Type" : "Select";
    return (
      <label className={fieldClass}>
        <span>{schema.label}</span>
        <select
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          data-searchable="true"
        >
          <option value="">{placeholder}</option>
          {(schema.options || []).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <SuggestionChips suggestions={suggestions} onPick={onPickSuggestion} />
        {validationMessages.length > 0 && (
          <div className="field-errors">
            {validationMessages.map((message) => (
              <div key={`${schema.key}-${message}`}>{message}</div>
            ))}
          </div>
        )}
      </label>
    );
  }

  if (schema.control === "radio-group") {
    return (
      <div className={fieldClass}>
        <span>{schema.label}</span>
        <div className="radio-group">
          {(schema.options || []).map((option) => (
            <label key={option.value}>
              <input
                type="radio"
                name={schema.key}
                value={option.value}
                checked={String(value) === option.value}
                onChange={(event) => onChange(event.target.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
        <SuggestionChips suggestions={suggestions} onPick={onPickSuggestion} />
      </div>
    );
  }

  return (
    <label className={fieldClass}>
      <span>{schema.label}</span>
      <input value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />
      <SuggestionChips suggestions={suggestions} onPick={onPickSuggestion} />
      {validationMessages.length > 0 && (
        <div className="field-errors">
          {validationMessages.map((message) => (
            <div key={`${schema.key}-${message}`}>{message}</div>
          ))}
        </div>
      )}
    </label>
  );
}
