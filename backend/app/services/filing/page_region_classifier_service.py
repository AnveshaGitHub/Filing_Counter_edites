from __future__ import annotations

import json
import re


class PageRegionClassifierService:
    def classify_regions(self, lines: list[dict]) -> list[dict]:
        regions: list[dict] = []

        for line in lines or []:
            text = str(line.get("text") or "")
            bbox = line.get("bbox") or [0, 0, 0, 0]
            region_type = self._classify_line(text)

            regions.append(
                {
                    "region_type": region_type,
                    "text": text,
                    "bbox": bbox,
                    "confidence": line.get("confidence"),
                }
            )

        return regions

    def _classify_line(self, text: str) -> str:
        low = text.lower()

        if "in the high court" in low or "principal seat" in low:
            return "header"

        if re.search(r"\b(appellant|applicant|petitioner|respondent|versus|vs\.?)\b", low):
            return "party_block"

        if re.search(r"\b(s/o|w/o|d/o|aged|age|occupation|r/o|district|tehsil)\b", low):
            return "party_detail"

        if "advocate" in low or "counsel" in low or "vakalatnama" in low:
            return "advocate_block"

        if "subject heading" in low or "provision of law" in low or "criminal law" in low:
            return "metadata_noise"

        if "court fees" in low or "fee type" in low:
            return "fee_table"

        if "index" in low or "particulars of document" in low:
            return "index"

        return "body"

    def region_summary_json(self, lines: list[dict]) -> str:
        return json.dumps(self.classify_regions(lines), ensure_ascii=False)
