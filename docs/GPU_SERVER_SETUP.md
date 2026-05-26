# Filing Counter GPU Server Setup

## Intended Extraction Flow

1. Render scanned/low-text PDF pages with PyMuPDF.
2. Run PaddleOCR first.
3. Fall back to Tesseract when Paddle is unavailable, fails, or produces weak text.
4. Run the Ollama vision model on targeted pages:
   - cause-title / party-detail pages with petitioner/respondent details
   - vakalatnama pages with advocate details
   - lower-court / impugned-order pages
   - pages containing Hindi, handwriting, garbled OCR, or low OCR confidence
5. Merge graph/rule candidates and vision candidates. Vision candidates remain review-required.

## Python Environment

Use a fresh virtual environment on the GPU server. Python 3.10 or 3.11 is the safest choice for Paddle GPU deployments.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r backend\requirements-gpu.txt
```

For a CPU-only server:

```powershell
.\venv\Scripts\python.exe -m pip install -r backend\requirements-cpu.txt
```

## System Dependencies

Install these outside Python:

- Tesseract OCR executable
- Ollama
- A vision model, for example:

```powershell
ollama pull llama3.2-vision
```

GPU Paddle installations must match the server CUDA/cuDNN stack. If `paddlepaddle-gpu` installation fails, install the Paddle build recommended for that server's CUDA version.

## Environment

Copy `.env.example` to `.env` and update these GPU values:

```env
PADDLE_OCR_USE_GPU=true
FILING_VISION_ENABLED=true
FILING_VISION_MODEL=llama3.2-vision
```

If Ollama runs on a different host:

```env
FILING_VISION_OLLAMA_URL=http://GPU_SERVER_IP:11434
```

## Quick Checks

```powershell
.\venv\Scripts\python.exe -m pip show paddleocr paddlepaddle-gpu pytesseract Pillow PyMuPDF
tesseract --version
ollama list
```

After processing a PDF, the `/process` response should show:

- `pages_with_paddle`
- `pages_with_tesseract`
- `pages_with_ocr`

The extraction candidate debug response should include the `vision` block when `FILING_VISION_ENABLED=true`.
