import { type Dispatch, type ReactNode, type SetStateAction, useState } from "react";

import type { FilingFullMetadata } from "../../types/filingFullMetadata";
import AdditionalAdvocateTab from "./AdditionalAdvocateTab";
import AdditionalPartyTab from "./AdditionalPartyTab";
import LowerCourtTab from "./LowerCourtTab";
import MainPartyTab from "./MainPartyTab";

const TABS = ["Main Party", "Additional Party", "Additional Advocate", "Lower Court"] as const;
type TabName = (typeof TABS)[number];

type Props = {
  documentId?: number;
  metadata: FilingFullMetadata;
  setMetadata: Dispatch<SetStateAction<FilingFullMetadata>>;
  mainParty: ReactNode;
  reviewActions: ReactNode;
  onAutofillMetadata: (section: "additional-parties" | "additional-advocates" | "lower-court") => Promise<void>;
  autofillingSection?: string;
};

export default function PhhcTabs({
  documentId,
  metadata,
  setMetadata,
  mainParty,
  reviewActions,
  onAutofillMetadata,
  autofillingSection,
}: Props) {
  const [active, setActive] = useState<TabName>("Main Party");

  const set = (key: string, value: unknown) => {
    setMetadata((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="phhc-tabs-wrap">
      <div className="phhc-tabs">
        {TABS.map((tab) => (
          <button key={tab} type="button" className={active === tab ? "active" : ""} onClick={() => setActive(tab)}>
            {tab}
          </button>
        ))}
      </div>

      <div className="phhc-tab-body">
        {active === "Main Party" && (
          <MainPartyTab>
            {mainParty}
            {reviewActions}
          </MainPartyTab>
        )}
        {active === "Additional Party" && (
          <AdditionalPartyTab
            documentId={documentId}
            metadata={metadata}
            set={set}
            onAutofill={onAutofillMetadata}
            autofilling={autofillingSection === "additional-parties"}
          />
        )}
        {active === "Additional Advocate" && (
          <AdditionalAdvocateTab
            documentId={documentId}
            metadata={metadata}
            set={set}
            onAutofill={onAutofillMetadata}
            autofilling={autofillingSection === "additional-advocates"}
          />
        )}
        {active === "Lower Court" && (
          <LowerCourtTab
            documentId={documentId}
            metadata={metadata}
            set={set}
            onAutofill={onAutofillMetadata}
            autofilling={autofillingSection === "lower-court"}
          />
        )}
      </div>
    </div>
  );
}
