import StatusPill from "../StatusPill";

type Props = {
  health: string;
  busy: string;
  onCheckHealth: () => void;
};

export default function PageHeader({ health, busy, onCheckHealth }: Props) {
  return (
    <header className="page-header">
      <div>
        <h1>Filing Counter</h1>
        <p>PHHC-style review screen with safe preview-first submission flow.</p>
      </div>
      <div className="header-actions">
        <button className="btn" onClick={onCheckHealth} disabled={busy !== ""}>
          {busy === "health" ? "Checking..." : "Check Backend Health"}
        </button>
        <StatusPill
          label={health}
          tone={health === "ok" ? "good" : health === "failed" ? "bad" : "neutral"}
        />
      </div>
    </header>
  );
}
