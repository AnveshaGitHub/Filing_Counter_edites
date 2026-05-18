from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class OCRResult:
    text: str
    confidence: float | None = None
    engine: str = "tesseract"
    raw_result: dict[str, Any] | None = None


class LocalOCRService:
    def __init__(self) -> None:
        self.enabled = (
            os.getenv("LOCAL_OCR_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.dpi = int(os.getenv("LOCAL_OCR_DPI", "200"))
        self.tesseract_cmd = os.getenv("TESSERACT_CMD")

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401

            return True
        except Exception:
            return False

    def configure_engine(self) -> None:
        if not self.enabled:
            return
        try:
            import pytesseract

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        except Exception:
            pass

    def ocr_pil_image(self, image: Any) -> OCRResult:
        import pytesseract

        self.configure_engine()
        text = pytesseract.image_to_string(image)
        raw_result = self._ocr_layout(image, pytesseract)
        return OCRResult(
            text=text or "",
            confidence=raw_result.get("avg_confidence") if raw_result else None,
            engine="tesseract",
            raw_result=raw_result,
        )

    def _ocr_layout(self, image: Any, pytesseract) -> dict[str, Any]:
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        except Exception:
            return {"words": [], "lines": [], "avg_confidence": 0.0}

        words: list[dict] = []
        line_groups: dict[tuple[int, int, int], list[dict]] = {}
        confidences: list[float] = []

        count = len(data.get("text", []))
        for idx in range(count):
            text = (data["text"][idx] or "").strip()
            if not text:
                continue

            try:
                conf = float(data["conf"][idx])
            except Exception:
                conf = -1.0
            confidence = conf / 100.0 if conf >= 0 else None
            if confidence is not None:
                confidences.append(confidence)

            x = float(data["left"][idx])
            y = float(data["top"][idx])
            w = float(data["width"][idx])
            h = float(data["height"][idx])
            word = {
                "text": text,
                "bbox": [x, y, x + w, y + h],
                "confidence": confidence,
            }
            words.append(word)

            key = (
                int(data.get("block_num", [0])[idx] or 0),
                int(data.get("par_num", [0])[idx] or 0),
                int(data.get("line_num", [0])[idx] or 0),
            )
            line_groups.setdefault(key, []).append(word)

        lines: list[dict] = []
        for _, group in sorted(line_groups.items()):
            xs0 = [w["bbox"][0] for w in group]
            ys0 = [w["bbox"][1] for w in group]
            xs1 = [w["bbox"][2] for w in group]
            ys1 = [w["bbox"][3] for w in group]
            line_conf = [w["confidence"] for w in group if w.get("confidence") is not None]
            lines.append(
                {
                    "text": " ".join(w["text"] for w in group),
                    "bbox": [min(xs0), min(ys0), max(xs1), max(ys1)],
                    "confidence": round(sum(line_conf) / len(line_conf), 4) if line_conf else None,
                }
            )

        avg = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        return {"words": words, "lines": lines, "avg_confidence": avg}

    def pixmap_to_pil(self, pixmap):
        from PIL import Image

        img_bytes = pixmap.tobytes("png")
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")
