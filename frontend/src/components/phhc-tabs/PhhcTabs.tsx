import { type Dispatch, type ReactNode, type SetStateAction, useState } from "react";

import type { FilingFullMetadata } from "../../types/filingFullMetadata";
import AdditionalAdvocateTab from "./AdditionalAdvocateTab";
import AdditionalPartyTab from "./AdditionalPartyTab";
import LowerCourtTab from "./LowerCourtTab";
import MainPartyTab from "./MainPartyTab";

const TABS = ["Main Party", "Additional Party", "Additional Advocate", "Lower Court"] as const;
type TabName = (typeof TABS)[number];

type Props = {
  metadata: FilingFullMetadata;
  setMetadata: Dispatch<SetStateAction<FilingFullMetadata>>;
  mainParty: ReactNode;
  reviewActions: ReactNode;
};

export default function PhhcTabs({ metadata, setMetadata, mainParty, reviewActions }: Props) {
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
        {active === "Additional Party" && <AdditionalPartyTab metadata={metadata} set={set} />}
        {active === "Additional Advocate" && <AdditionalAdvocateTab metadata={metadata} set={set} />}
        {active === "Lower Court" && <LowerCourtTab metadata={metadata} set={set} />}
      </div>
    </div>
  );
}
