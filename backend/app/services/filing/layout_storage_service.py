from __future__ import annotations

import json
import re
from typing import Any


class LayoutStorageService:
    def normalize_paddle_result(self, ocr_result: Any) -> tuple[list[dict], list[dict], float]:
        """
        Accepts PaddleOCR-like output or normalized dicts with words/lines.
        Returns words/lines normalized for DB JSON storage.
        """
        if not ocr_result:
            return [], [], 0.0

        if isinstance(ocr_result, dict) and ("words" in ocr_result or "lines" in ocr_result):
            lines = [self._normalize_line(line) for line in ocr_result.get("lines") or []]
            lines = [line for line in lines if line.get("text")]
            words = [self._normalize_line(word) for word in ocr_result.get("words") or []]
            words = [word for word in words if word.get("text")]
            if not words:
                words = self.lines_to_words(lines)
            avg = self._avg_confidence(words or lines)
            return words, lines, avg

        lines: list[dict] = []
        confidences: list[float] = []

        items = ocr_result
        if isinstance(items, dict):
            items = items.get("result") or items.get("lines") or items.get("ocr") or []

        if isinstance(items, list) and len(items) == 1 and isinstance(items[0], list):
            if items and items[0] and isinstance(items[0][0], (list, tuple)):
                items = items[0]

        for item in items:
            try:
                box = item[0]
                payload = item[1]
                text = payload[0] if isinstance(payload, (list, tuple)) else ""
                conf = float(payload[1]) if isinstance(payload, (list, tuple)) and len(payload) > 1 else None
            except Exception:
                continue

            if not text:
                continue

            bbox = self._bbox_from_box(box)
            if conf is not None:
                confidences.append(conf)

            lines.append({"text": str(text), "bbox": bbox, "confidence": conf})

        words = self.lines_to_words(lines)
        avg = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        return words, lines, avg

    def layout_from_text(self, text: str | None) -> tuple[list[dict], list[dict], float]:
        lines = [
            {
                "text": line.strip(),
                "bbox": [0.0, float(idx * 20), 1000.0, float(idx * 20 + 15)],
                "confidence": None,
            }
            for idx, line in enumerate((text or "").splitlines())
            if line.strip()
        ]
        return self.lines_to_words(lines), lines, 0.0

    def lines_to_words(self, lines: list[dict]) -> list[dict]:
        words: list[dict] = []

        for line in lines:
            text = line.get("text") or ""
            bbox = line.get("bbox") or [0, 0, 0, 0]
            tokens = [t for t in re.split(r"\s+", text.strip()) if t]

            if not tokens:
                continue

            x0, y0, x1, y1 = bbox
            width = max(float(x1) - float(x0), 1.0)
            step = width / len(tokens)

            for idx, token in enumerate(tokens):
                wx0 = float(x0) + idx * step
                wx1 = float(x0) + (idx + 1) * step
                words.append(
                    {
                        "text": token,
                        "bbox": [wx0, float(y0), wx1, float(y1)],
                        "confidence": line.get("confidence"),
                    }
                )

        return words

    def save_layout_to_page_row(
        self,
        page_row,
        words: list[dict],
        lines: list[dict],
        avg_confidence: float,
        regions: list[dict] | None = None,
    ) -> None:
        if hasattr(page_row, "ocr_words_json"):
            page_row.ocr_words_json = json.dumps(words, ensure_ascii=False)

        if hasattr(page_row, "ocr_lines_json"):
            page_row.ocr_lines_json = json.dumps(lines, ensure_ascii=False)

        if hasattr(page_row, "ocr_avg_confidence"):
            page_row.ocr_avg_confidence = avg_confidence

        if regions is not None and hasattr(page_row, "page_regions_json"):
            page_row.page_regions_json = json.dumps(regions, ensure_ascii=False)

    def _normalize_line(self, item: dict) -> dict:
        confidence = item.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else None
        except Exception:
            confidence = None
        return {
            "text": str(item.get("text") or ""),
            "bbox": self._bbox_from_box(item.get("bbox") or item.get("box")),
            "confidence": confidence,
        }

    def _avg_confidence(self, items: list[dict]) -> float:
        confidences = []
        for item in items:
            confidence = item.get("confidence")
            if confidence is not None:
                confidences.append(float(confidence))
        return round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    def _bbox_from_box(self, box: Any) -> list[float]:
        if isinstance(box, (list, tuple)) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
            return [float(v) for v in box]

        if isinstance(box, (list, tuple)) and box and isinstance(box[0], (list, tuple)):
            xs = [float(p[0]) for p in box if isinstance(p, (list, tuple)) and len(p) >= 2]
            ys = [float(p[1]) for p in box if isinstance(p, (list, tuple)) and len(p) >= 2]
            if xs and ys:
                return [min(xs), min(ys), max(xs), max(ys)]

        return [0.0, 0.0, 0.0, 0.0]
