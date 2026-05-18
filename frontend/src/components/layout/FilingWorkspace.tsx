import { useState, type ReactNode } from "react";
import PdfViewerPanel from "../pdf/PdfViewerPanel";
import type { EFilingFetchResponse } from "../../types/efiling";
import type { LocalTestDocumentResponse } from "../../types/testDocuments";

type PdfWidthMode = "narrow" | "medium" | "wide";

type Props = {
  utilityPanel: ReactNode;
  children: ReactNode;
  efilingData?: EFilingFetchResponse | null;
  documentInfo?: LocalTestDocumentResponse | null;
  pdfUrl?: string | null;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  onBack: () => void;
};

export default function FilingWorkspace({
  utilityPanel,
  children,
  efilingData,
  documentInfo,
  pdfUrl,
  activeTab = "Main Party",
  onTabChange,
  onBack,
}: Props) {
  const [pdfVisible, setPdfVisible] = useState(true);
  const [pdfWidthMode, setPdfWidthMode] = useState<PdfWidthMode>("medium");

  return (
    <div className="workspace-page">
      <div className="workspace-topbar">
        <div className="brand">PHHC</div>
        <div className="top-search">Enter keyword</div>
      </div>

      <main className="workspace-main">
          {(efilingData || documentInfo) && (
            <div className="diary-banner">
              {efilingData?.diary_no
                ? `Diary No. ${efilingData.diary_no} already generated.`
                : `Local Document ID ${documentInfo?.id} loaded for filing review.`}
            </div>
          )}

          {void activeTab}
          {void onTabChange}

          <div className={`review-split review-split--${pdfVisible ? pdfWidthMode : "full"}`}>
            <aside className="utility-pane">
              <section className="section-card">
                <div className="section-card__header">
                  <h2>Workflow</h2>
                </div>
                <div className="section-card__body">
                  <div className="stack">
                    <button className="btn" type="button" onClick={onBack}>Back to Search</button>
                    <button className="btn" type="button">Consume Report</button>
                  </div>
                </div>
              </section>
              {utilityPanel}
            </aside>

            <section className="review-form-pane">{children}</section>

            <PdfViewerPanel
              visible={pdfVisible}
              widthMode={pdfWidthMode}
              pdfUrl={pdfUrl}
              onToggleVisible={() => setPdfVisible((value) => !value)}
              onWidthModeChange={setPdfWidthMode}
            />
          </div>
        </main>
    </div>
  );
}
