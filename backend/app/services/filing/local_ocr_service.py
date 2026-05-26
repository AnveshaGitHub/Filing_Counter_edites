from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class OCRResult:
    text: str
    confidence: float | None = None
    engine: str = "unknown"
    raw_result: dict[str, Any] | None = None


class LocalOCRService:
    def __init__(self) -> None:
        self.enabled = (
            os.getenv("LOCAL_OCR_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.dpi = int(os.getenv("LOCAL_OCR_DPI", "200"))
        self.primary_engine = os.getenv("LOCAL_OCR_PRIMARY_ENGINE", "paddle").strip().lower()
        self.fallback_engine = os.getenv("LOCAL_OCR_FALLBACK_ENGINE", "tesseract").strip().lower()
        self.min_confidence = float(os.getenv("LOCAL_OCR_MIN_CONFIDENCE", "0.55"))
        self.paddle_lang = os.getenv("PADDLE_OCR_LANG", "en").strip() or "en"
        self.paddle_use_gpu = (
            os.getenv("PADDLE_OCR_USE_GPU", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.tesseract_cmd = os.getenv("TESSERACT_CMD")
        self._paddle_ocr: Any | None = None

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        return self.is_paddle_available() or self.is_tesseract_available()

    def is_paddle_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            import paddleocr  # noqa: F401

            return True
        except Exception:
            return False

    def is_tesseract_available(self) -> bool:
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
        if not self.enabled:
            return OCRResult(text="", confidence=0.0, engine="disabled", raw_result=None)

        primary = self.primary_engine
        fallback = self.fallback_engine

        if primary == "paddle":
            primary_result = self.ocr_with_paddle(image)
            if self._is_strong_result(primary_result) or fallback != "tesseract":
                return primary_result

            fallback_result = self.ocr_with_tesseract(image)
            if self._prefer_fallback(primary_result, fallback_result):
                return fallback_result
            return primary_result

        if primary == "tesseract":
            return self.ocr_with_tesseract(image)

        return OCRResult(text="", confidence=0.0, engine=f"unsupported:{primary}", raw_result=None)

    def ocr_with_paddle(self, image: Any) -> OCRResult:
        try:
            ocr = self._get_paddle_ocr()
            if ocr is None:
                return OCRResult(text="", confidence=0.0, engine="paddle_unavailable", raw_result=None)

            try:
                import numpy as np

                ocr_input = np.array(image.convert("RGB") if hasattr(image, "convert") else image)
            except Exception:
                ocr_input = image

            result = ocr.ocr(ocr_input, cls=True)
            text, confidence = self._paddle_text_and_confidence(result)
            return OCRResult(
                text=text,
                confidence=confidence,
                engine="paddle",
                raw_result={"result": result},
            )
        except Exception as exc:
            return OCRResult(
                text="",
                confidence=0.0,
                engine="paddle_failed",
                raw_result={"error": str(exc)},
            )

    def _get_paddle_ocr(self) -> Any | None:
        if self._paddle_ocr is not None:
            return self._paddle_ocr

        try:
            from paddleocr import PaddleOCR
        except Exception:
            return None

        try:
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.paddle_lang,
                use_gpu=self.paddle_use_gpu,
                show_log=False,
            )
        except TypeError:
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.paddle_lang,
                use_gpu=self.paddle_use_gpu,
            )
        return self._paddle_ocr

    def _paddle_text_and_confidence(self, result: Any) -> tuple[str, float | None]:
        lines: list[str] = []
        confidences: list[float] = []

        items = result or []
        if isinstance(items, list) and len(items) == 1 and isinstance(items[0], list):
            items = items[0]

        for item in items:
            try:
                payload = item[1]
                text = payload[0] if isinstance(payload, (list, tuple)) else ""
                confidence = payload[1] if isinstance(payload, (list, tuple)) and len(payload) > 1 else None
            except Exception:
                continue

            if text:
                lines.append(str(text))
            if confidence is not None:
                try:
                    confidences.append(float(confidence))
                except Exception:
                    pass

        avg = round(sum(confidences) / len(confidences), 4) if confidences else None
        return "\n".join(lines), avg

    def _is_strong_result(self, result: OCRResult) -> bool:
        text = (result.text or "").strip()
        confidence = result.confidence if result.confidence is not None else 0.0
        return len(text) >= 50 and confidence >= self.min_confidence

    def _prefer_fallback(self, primary: OCRResult, fallback: OCRResult) -> bool:
        primary_text = (primary.text or "").strip()
        fallback_text = (fallback.text or "").strip()
        if not fallback_text:
            return False
        if len(fallback_text) > max(len(primary_text) * 1.25, len(primary_text) + 80):
            return True
        primary_conf = primary.confidence if primary.confidence is not None else 0.0
        fallback_conf = fallback.confidence if fallback.confidence is not None else 0.0
        return primary_conf < self.min_confidence and fallback_conf > primary_conf

    def ocr_with_tesseract(self, image: Any) -> OCRResult:
        if not self.is_tesseract_available():
            return OCRResult(text="", confidence=0.0, engine="tesseract_unavailable", raw_result=None)

        return self._ocr_with_tesseract(image)

    def _ocr_with_tesseract(self, image: Any) -> OCRResult:
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
