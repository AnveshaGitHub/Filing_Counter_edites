from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.filing.layout_party_extractor.layout_models import LayoutLine, LayoutWord


class LayoutLineBuilder:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load_lines(self, document_id: int, allowed_page_nos: set[int] | None = None) -> list[LayoutLine]:
        rows = self._load_page_rows(document_id)
        lines: list[LayoutLine] = []

        for row in rows:
            page_no = int(getattr(row, "page_no", 0) or 0)
            if allowed_page_nos and page_no not in allowed_page_nos:
                continue

            words = self._extract_words_from_row(row)
            if words:
                lines.extend(self._build_lines_from_words(page_no, words))
                continue

            text = getattr(row, "ocr_text", None) or getattr(row, "text", None) or ""
            lines.extend(self._build_lines_from_text(page_no, text))

        return lines

    def _load_page_rows(self, document_id: int) -> list[Any]:
        try:
            from app.models.local_test_document_page import LocalTestDocumentPage

            rows = (
                self.db.query(LocalTestDocumentPage)
                .filter(LocalTestDocumentPage.document_id == document_id)
                .order_by(LocalTestDocumentPage.page_no.asc())
                .all()
            )
            if rows:
                return rows
        except Exception:
            pass

        try:
            from app.models.document_page import DocumentPage

            return (
                self.db.query(DocumentPage)
                .filter(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_no.asc())
                .all()
            )
        except Exception:
            return []

    def _extract_words_from_row(self, row: Any) -> list[LayoutWord]:
        raw = None
        for attr in ["ocr_words_json", "words_json", "ocr_json", "layout_json"]:
            if hasattr(row, attr):
                raw = getattr(row, attr)
                if raw:
                    break

        if not raw:
            return []

        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return []

        if isinstance(data, dict):
            data = data.get("words") or data.get("lines") or data.get("result") or []

        if not isinstance(data, list):
            return []

        words: list[LayoutWord] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            text = item.get("text") or item.get("word") or item.get("value")
            if not text:
                continue

            bbox = item.get("bbox") or item.get("box")
            x0 = y0 = x1 = y1 = 0.0

            if isinstance(bbox, list):
                if len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox):
                    x0, y0, x1, y1 = map(float, bbox)
                elif len(bbox) >= 4 and isinstance(bbox[0], list):
                    xs = [float(p[0]) for p in bbox if isinstance(p, list) and len(p) >= 2]
                    ys = [float(p[1]) for p in bbox if isinstance(p, list) and len(p) >= 2]
                    if xs and ys:
                        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

            words.append(
                LayoutWord(
                    text=str(text),
                    x0=float(item.get("x0", x0) or x0),
                    y0=float(item.get("y0", y0) or y0),
                    x1=float(item.get("x1", x1) or x1),
                    y1=float(item.get("y1", y1) or y1),
                    conf=item.get("conf") or item.get("confidence"),
                )
            )

        return words

    def _build_lines_from_words(self, page_no: int, words: list[LayoutWord]) -> list[LayoutLine]:
        words = sorted(words, key=lambda w: (w.y0, w.x0))
        rows: list[list[LayoutWord]] = []

        for word in words:
            placed = False
            cy = (word.y0 + word.y1) / 2
            height = max(word.y1 - word.y0, 10.0)

            for row in rows:
                row_cy = sum((w.y0 + w.y1) / 2 for w in row) / max(len(row), 1)
                row_height = max((w.y1 - w.y0 for w in row), default=10.0)
                if abs(cy - row_cy) <= max(10.0, min(14.0, max(height, row_height) * 0.8)):
                    row.append(word)
                    placed = True
                    break

            if not placed:
                rows.append([word])

        lines: list[LayoutLine] = []
        for row in rows:
            row = sorted(row, key=lambda w: w.x0)
            text = self._clean(" ".join(w.text for w in row))
            if not text:
                continue
            lines.append(
                LayoutLine(
                    text=text,
                    page_no=page_no,
                    x0=min(w.x0 for w in row),
                    y0=min(w.y0 for w in row),
                    x1=max(w.x1 for w in row),
                    y1=max(w.y1 for w in row),
                    words=row,
                )
            )

        return lines

    def _build_lines_from_text(self, page_no: int, text: str) -> list[LayoutLine]:
        raw_lines = re.split(r"[\n\r]+", text or "")
        if len(raw_lines) <= 1:
            raw_lines = re.split(r"\s{2,}", text or "")

        out: list[LayoutLine] = []
        for idx, line in enumerate(raw_lines):
            clean = self._clean(line)
            if not clean:
                continue
            out.append(
                LayoutLine(
                    text=clean,
                    page_no=page_no,
                    y0=float(idx * 20),
                    y1=float(idx * 20 + 10),
                )
            )

        return out

    def _clean(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.replace("\u200c", " ").replace("\u200d", " ")
        value = re.sub(r"\s+", " ", value)
        return value.strip()
