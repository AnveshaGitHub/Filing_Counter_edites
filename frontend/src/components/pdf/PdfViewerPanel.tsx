type PdfWidthMode = "narrow" | "medium" | "wide";

type Props = {
  visible: boolean;
  widthMode: PdfWidthMode;
  pdfUrl?: string | null;
  onToggleVisible: () => void;
  onWidthModeChange: (mode: PdfWidthMode) => void;
};

export default function PdfViewerPanel({
  visible,
  widthMode,
  pdfUrl,
  onToggleVisible,
  onWidthModeChange,
}: Props) {
  if (!visible) {
    return (
      <div className="pdf-hidden-bar">
        <button className="btn" type="button" onClick={onToggleVisible}>Show Softcopy Panel</button>
      </div>
    );
  }

  return (
    <aside className={`pdf-panel pdf-panel--${widthMode}`}>
      <div className="pdf-toolbar">
        <button
          className="btn"
          type="button"
          onClick={() => {
            if (pdfUrl) window.open(pdfUrl, "_blank", "noopener,noreferrer");
          }}
          disabled={!pdfUrl}
        >
          Open Document Tab
        </button>
        <button className="btn" type="button" onClick={onToggleVisible}>Hide Softcopy Panel</button>
        <button className={`btn ${widthMode === "narrow" ? "btn-primary" : ""}`} type="button" onClick={() => onWidthModeChange("narrow")}>Narrow</button>
        <button className={`btn ${widthMode === "medium" ? "btn-primary" : ""}`} type="button" onClick={() => onWidthModeChange("medium")}>Medium</button>
        <button className={`btn ${widthMode === "wide" ? "btn-primary" : ""}`} type="button" onClick={() => onWidthModeChange("wide")}>Wide</button>
      </div>

      <div className="pdf-frame">
        {pdfUrl ? (
          <iframe key={pdfUrl} src={pdfUrl} title="Softcopy PDF" />
        ) : (
          <div className="pdf-placeholder">
            PDF viewer will appear here after upload. Fetched e-filing records will use the future indexed PDF adapter.
          </div>
        )}
      </div>
    </aside>
  );
}
