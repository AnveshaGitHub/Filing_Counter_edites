type Props = {
  label: string;
  tone?: "neutral" | "good" | "warn" | "bad";
};

export default function StatusPill({ label, tone = "neutral" }: Props) {
  return <span className={`status-pill status-pill--${tone}`}>{label}</span>;
}
