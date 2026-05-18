from __future__ import annotations

import sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.filing.local_ocr_service import LocalOCRService  # noqa


def main(pdf_path: str) -> None:
    path = Path(pdf_path)
    if not path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    pdf = fitz.open(str(path))
    ocr_service = LocalOCRService()

    print(f"PDF: {path}")
    print(f"OCR enabled: {ocr_service.enabled}")
    print(f"OCR available: {ocr_service.is_available()}")
    print("-" * 80)

    for idx, page in enumerate(pdf):
        page_no = idx + 1
        embedded_text = (page.get_text("text") or "").strip()

        ocr_text = ""
        if ocr_service.is_available():
            try:
                zoom = ocr_service.dpi / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                pil_img = ocr_service.pixmap_to_pil(pix)
                result = ocr_service.ocr_pil_image(pil_img)
                ocr_text = (result.text or "").strip()
            except Exception as exc:
                ocr_text = f"[OCR ERROR] {exc}"

        print(f"page={page_no}")
        print(f"  embedded_text_len={len(embedded_text)}")
        print(f"  ocr_text_len={len(ocr_text) if not ocr_text.startswith('[OCR ERROR]') else 0}")
        print(f"  embedded_preview={repr(embedded_text[:120])}")
        print(f"  ocr_preview={repr(ocr_text[:120])}")
        print("-" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/debug_local_pdf_text.py <path-to-pdf>")
    main(sys.argv[1])
