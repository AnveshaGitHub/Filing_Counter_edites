import type { FieldCandidate } from "../types/filingExtraction";

type Props = {
  suggestions?: FieldCandidate[];
  onPick: (value: string) => void;
};

function truncate(text: string, maxLen = 42) {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1).trimEnd() + "...";
}

export default function SuggestionChips({ suggestions = [], onPick }: Props) {
  const visible = suggestions.slice(0, 3);
  if (!visible.length) return null;

  return (
    <div className="chips">
      {visible.map((s, idx) => {
        const value = s.normalized_value || s.value;
        return (
          <button
            type="button"
            key={`${value}-${idx}`}
            className="chip"
            onClick={() => onPick(value)}
            title={value}
          >
            {truncate(value)}
          </button>
        );
      })}
    </div>
  );
}
