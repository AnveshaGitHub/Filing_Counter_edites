from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from datetime import datetime
import fitz
from sqlalchemy import MetaData, Table, select
from sqlalchemy.orm import Session

from app.models.local_test_document import LocalTestDocument
from app.models.local_test_document_page import LocalTestDocumentPage
from app.integrations.vector_store.chroma_retriever import ChromaRetriever
from app.services.filing.utils.pdf_text_chunker import build_page_chunks
from app.services.filing.local_ocr_service import LocalOCRService
from app.services.filing.layout_storage_service import LayoutStorageService
from app.services.filing.page_classifier_service import PageClassifierService
from app.services.filing.page_region_classifier_service import PageRegionClassifierService
from app.services.filing.utils.page_layout_analyzer import classify_page
from app.services.filing.utils.text_cleaner import clean_page_text
from app.services.filing.field_page_router_service import FieldPageRouterService
from app.services.filing.routed_region_extractor_service import RoutedRegionExtractorService

logger = logging.getLogger(__name__)


class LocalTestDocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage_dir = Path("./test_pdfs")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.retriever = ChromaRetriever()
        self.ocr_service = LocalOCRService()
        self.layout_storage = LayoutStorageService()
        self.page_classifier = PageClassifierService()
        self.region_classifier = PageRegionClassifierService()

    def create_uploaded_document(self, original_filename: str, content: bytes) -> LocalTestDocument:
        row = LocalTestDocument(
            original_filename=original_filename,
            stored_path="",
            status="uploaded",
            source="local_test_upload",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

        safe_name = f"{row.id}_{Path(original_filename).name}"
        stored_path = self.storage_dir / safe_name
        stored_path.write_bytes(content)

        row.stored_path = str(stored_path)
        row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_document(self, document_id: int) -> LocalTestDocument | None:
        return (
            self.db.query(LocalTestDocument)
            .filter(LocalTestDocument.id == document_id)
            .first()
        )

    def _extract_page_text(self, page) -> tuple[str, str, float | None, dict | None]:
        """
        Returns:
          text, extraction_method, confidence, raw OCR layout
        """
        embedded_text = page.get_text("text") or ""
        embedded_text = embedded_text.strip()

        # Strong enough embedded text -> use it directly
        if len(embedded_text) >= 50:
            return embedded_text, "pdf_text", 1.0, None

        # OCR fallback
        if not self.ocr_service.is_available():
            return embedded_text, "pdf_text" if embedded_text else "none", 1.0 if embedded_text else 0.0, None

        try:
            zoom = self.ocr_service.dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pil_img = self.ocr_service.pixmap_to_pil(pix)
            ocr_result = self.ocr_service.ocr_pil_image(pil_img)
            ocr_text = (ocr_result.text or "").strip()

            if len(ocr_text) > len(embedded_text):
                return ocr_text, f"ocr_{ocr_result.engine}", ocr_result.confidence, ocr_result.raw_result

            return embedded_text, "pdf_text" if embedded_text else "none", 1.0 if embedded_text else 0.0, None

        except Exception:
            logger.exception("[LOCAL OCR] OCR fallback failed")
            return embedded_text, "pdf_text" if embedded_text else "none", 1.0 if embedded_text else 0.0, None

    def process_document(self, document_id: int) -> dict:
        doc_row = self.get_document(document_id)
        if not doc_row:
            raise ValueError("local_test_document_not_found")

        pdf_path = Path(doc_row.stored_path)
        if not pdf_path.exists():
            raise ValueError("stored_pdf_not_found")

        (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()

        if self.retriever.collection is not None:
            try:
                self.retriever.collection.delete(
                    where={"document_id": document_id, "source": "local_test_upload"}
                )
            except Exception:
                pass

        pdf = fitz.open(str(pdf_path))

        page_rows: list[LocalTestDocumentPage] = []
        total_chunks = 0
        pages_with_embedded_text = 0
        pages_with_ocr = 0
        pages_with_paddle = 0
        pages_with_tesseract = 0

        for idx, page in enumerate(pdf):
            page_no = idx + 1

            raw_embedded_text = (page.get_text("text") or "").strip()
            logger.info("[LOCAL TEST] page=%s, embedded_text_len=%s", page_no, len(raw_embedded_text))

            final_text_raw, extraction_method, confidence, raw_ocr_layout = self._extract_page_text(page)
            final_text = clean_page_text(final_text_raw)
            if raw_ocr_layout:
                words, lines, avg_confidence = self.layout_storage.normalize_paddle_result(raw_ocr_layout)
            else:
                words, lines, avg_confidence = self.layout_storage.layout_from_text(final_text)
            regions = self.region_classifier.classify_regions(lines)
            text_length = len(final_text)
            layout = classify_page(final_text)
            try:
                page_classification = self.page_classifier.classify_text(
                    page_no=page_no,
                    text=final_text,
                )
                logger.info(
                    "[PAGE CLASSIFIER] page=%s, type=%s, confidence=%s, reasons=%s",
                    page_no,
                    page_classification.page_type,
                    page_classification.confidence,
                    page_classification.reasons,
                )
            except Exception:
                logger.exception("[PAGE CLASSIFIER] failed page=%s", page_no)

            if extraction_method == "pdf_text" and text_length > 0:
                pages_with_embedded_text += 1
            elif extraction_method.startswith("ocr_") and text_length > 0:
                pages_with_ocr += 1
                if extraction_method == "ocr_paddle":
                    pages_with_paddle += 1
                elif extraction_method == "ocr_tesseract":
                    pages_with_tesseract += 1

            logger.info(
                "[LOCAL TEST] page=%s, method=%s, raw_final_text_len=%s, cleaned_text_len=%s, page_types=%s",
                page_no,
                extraction_method,
                len((final_text_raw or "").strip()),
                text_length,
                layout.get("page_types"),
            )

            page_row = LocalTestDocumentPage(
                document_id=document_id,
                page_no=page_no,
                ocr_text=final_text,
                ocr_confidence=confidence,
                extraction_method=extraction_method,
                text_length=text_length,
            )
            self.layout_storage.save_layout_to_page_row(
                page_row=page_row,
                words=words,
                lines=lines,
                avg_confidence=avg_confidence,
                regions=regions,
            )
            self.db.add(page_row)
            page_rows.append(page_row)

            page_chunks = build_page_chunks(
                page_no=page_no,
                text=final_text,
                chunk_size=700,
                overlap=100,
            )

            logger.info("[LOCAL TEST] page=%s, chunk_count=%s", page_no, len(page_chunks))

            if self.retriever.collection is not None:
                for chunk in page_chunks:
                    self.retriever.collection.add(
                        documents=[chunk.text],
                        metadatas=[
                            {
                                "document_id": document_id,
                                "page_no": chunk.page_no,
                                "chunk_index": chunk.chunk_index,
                                "source": "local_test_upload",
                            }
                        ],
                        ids=[f"localtest_{document_id}_{chunk.page_no}_{chunk.chunk_index}"],
                    )
                    total_chunks += 1
            else:
                total_chunks += len(page_chunks)

        self.db.commit()

        doc_row.status = "processed"
        doc_row.notes = (
            f"pages={len(page_rows)}, chunks={total_chunks}, "
            f"pdf_text_pages={pages_with_embedded_text}, "
            f"ocr_pages={pages_with_ocr}, "
            f"paddle_pages={pages_with_paddle}, "
            f"tesseract_pages={pages_with_tesseract}"
        )
        doc_row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc_row)

        try:
            FieldPageRouterService(self.db).build_routes(document_id=document_id)
        except Exception:
            logger.exception("[FIELD ROUTER] failed document_id=%s", document_id)

        try:
            RoutedRegionExtractorService(self.db).build_regions(document_id=document_id)
        except Exception:
            logger.exception("[ROUTED REGION] failed document_id=%s", document_id)

        return {
            "document_id": document_id,
            "status": doc_row.status,
            "pages": len(page_rows),
            "chunks": total_chunks,
            "pages_with_embedded_text": pages_with_embedded_text,
            "pages_with_ocr": pages_with_ocr,
            "pages_with_paddle": pages_with_paddle,
            "pages_with_tesseract": pages_with_tesseract,
        }

    def build_ocr_pdf_file(self, document_id: int) -> tuple[bytes, str]:
        doc_row = self.get_document(document_id)
        if not doc_row:
            raise ValueError("local_test_document_not_found")

        page_rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
        if not page_rows:
            raise ValueError("local_test_document_not_processed")

        base_name = Path(doc_row.original_filename or f"document_{document_id}").stem
        filename = f"{document_id}_{base_name}_ocr_text.pdf"
        return self._create_ocr_pdf(doc_row.original_filename, page_rows), filename

    def _create_ocr_pdf(self, original_filename: str, page_rows: list[LocalTestDocumentPage]) -> bytes:
        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        margin = 48
        y = margin
        line_height = 14
        max_y = 800

        def add_line(text: str, font_size: int = 10, bold: bool = False) -> None:
            nonlocal page, y
            if y > max_y:
                page = pdf.new_page(width=595, height=842)
                y = margin
            fontname = "helv"
            page.insert_text(
                (margin, y),
                self._pdf_safe_text(text),
                fontsize=font_size,
                fontname=fontname,
                color=(0, 0, 0),
            )
            y += line_height + (4 if bold else 0)

        header_lines = [
            "Extracted OCR Text",
            f"Source file: {original_filename or '-'}",
            f"Pages: {len(page_rows)}",
            "",
        ]

        for index, line in enumerate(header_lines):
            add_line(line, font_size=16 if index == 0 else 10, bold=index == 0)

        for page_row in page_rows:
            confidence = page_row.ocr_confidence
            if confidence is None:
                confidence = page_row.ocr_avg_confidence
            confidence_text = f"{confidence:.2%}" if confidence is not None else "N/A"
            method = page_row.extraction_method or "unknown"

            add_line(f"Page {page_row.page_no}", font_size=13, bold=True)
            add_line(f"Confidence score: {confidence_text}")
            add_line(f"Extraction method: {method}")

            text = (page_row.ocr_text or "").strip()
            if text:
                for line in text.splitlines():
                    wrapped_lines = textwrap.wrap(
                        line,
                        width=92,
                        replace_whitespace=False,
                        drop_whitespace=False,
                    ) or [""]
                    for wrapped_line in wrapped_lines:
                        add_line(wrapped_line)
            else:
                add_line("[No OCR text extracted]")
            add_line("")

        content = pdf.tobytes()
        pdf.close()
        return content

    def _pdf_safe_text(self, text: str) -> str:
        return "".join(
            char
            for char in str(text)
            if char == "\t" or ord(char) >= 32
        )

    def ensure_main_document_stub(self, document_id: int) -> bool:
        """
        Best-effort helper for environments where extraction tables enforce
        FK(document_id -> documents.id). This keeps local test flow isolated
        while remaining compatible with existing schemas.
        """
        try:
            bind = self.db.get_bind()
            metadata = MetaData()
            documents = Table("documents", metadata, autoload_with=bind)

            existing = self.db.execute(
                select(documents.c.id).where(documents.c.id == document_id)
            ).first()
            if existing:
                return True

            payload: dict[str, object] = {"id": document_id}

            for col in documents.columns:
                if col.name == "id":
                    continue
                if col.nullable or col.default is not None or col.server_default is not None:
                    continue
                try:
                    pytype = col.type.python_type  # type: ignore[attr-defined]
                except Exception:
                    pytype = str

                if pytype is str:
                    payload[col.name] = "local_test_upload"
                elif pytype is int:
                    payload[col.name] = 0
                elif pytype is float:
                    payload[col.name] = 0.0
                elif pytype is bool:
                    payload[col.name] = False
                elif pytype is datetime:
                    payload[col.name] = datetime.utcnow()
                else:
                    payload[col.name] = "local_test_upload"

            self.db.execute(documents.insert().values(**payload))
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
