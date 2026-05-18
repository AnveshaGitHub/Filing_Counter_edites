from __future__ import annotations

import re

from app.services.filing.layout_party_extractor.bilingual_legal_labels import (
    PETITIONER_LABELS,
    RESPONDENT_LABELS,
)
from app.services.filing.layout_party_extractor.layout_models import LayoutLine, PartyBlock


class PartyBlockParser:
    def parse(self, lines: list[LayoutLine]) -> list[PartyBlock]:
        by_page: dict[int, list[LayoutLine]] = {}
        for line in lines:
            by_page.setdefault(line.page_no, []).append(line)

        blocks: list[PartyBlock] = []
        for page_no, page_lines in by_page.items():
            page_lines = sorted(page_lines, key=lambda line: (line.y0, line.x0))
            blocks.extend(self._parse_page(page_no, page_lines))

        return blocks

    def _parse_page(self, page_no: int, lines: list[LayoutLine]) -> list[PartyBlock]:
        markers: list[tuple[int, str, str]] = []

        for idx, line in enumerate(lines):
            text = line.text
            if self._has_label(text, PETITIONER_LABELS):
                markers.append((idx, "petitioner", self._matched_label(text, PETITIONER_LABELS)))
            elif self._has_label(text, RESPONDENT_LABELS):
                markers.append((idx, "respondent", self._matched_label(text, RESPONDENT_LABELS)))

        if not markers:
            return self._parse_versus_blocks(page_no, lines)

        blocks: list[PartyBlock] = []
        for pos, (idx, side, label) in enumerate(markers):
            end = markers[pos + 1][0] if pos + 1 < len(markers) else min(len(lines), idx + 8)
            block_lines = lines[idx:end]
            if block_lines:
                blocks.append(
                    PartyBlock(
                        side=side,
                        page_no=page_no,
                        label=label,
                        lines=block_lines,
                        confidence=0.85,
                    )
                )

        return blocks

    def _parse_versus_blocks(self, page_no: int, lines: list[LayoutLine]) -> list[PartyBlock]:
        blocks: list[PartyBlock] = []

        for idx, line in enumerate(lines):
            if re.fullmatch(r"(VERSUS|VS\.?|V/S|बनाम)", line.text.strip(), re.I):
                before = lines[max(0, idx - 4):idx]
                after = lines[idx + 1:min(len(lines), idx + 5)]

                if before:
                    blocks.append(
                        PartyBlock(
                            side="petitioner",
                            page_no=page_no,
                            label="VERSUS_BEFORE",
                            lines=before,
                            confidence=0.72,
                        )
                    )
                if after:
                    blocks.append(
                        PartyBlock(
                            side="respondent",
                            page_no=page_no,
                            label="VERSUS_AFTER",
                            lines=after,
                            confidence=0.72,
                        )
                    )

        return blocks

    def _has_label(self, text: str, labels: list[str]) -> bool:
        low = text.lower()
        return any(label.lower() in low for label in labels)

    def _matched_label(self, text: str, labels: list[str]) -> str:
        low = text.lower()
        for label in labels:
            if label.lower() in low:
                return label
        return labels[0]
