from __future__ import annotations

import json
import sys
from pathlib import Path
import requests


BASE_URL = "http://127.0.0.1:8030/api/v1"


def main(pdf_path: str) -> None:
    file_path = Path(pdf_path)
    if not file_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    with file_path.open("rb") as f:
        resp = requests.post(
            f"{BASE_URL}/test-documents/upload",
            files={"file": (file_path.name, f, "application/pdf")},
            timeout=120,
        )
    resp.raise_for_status()
    uploaded = resp.json()
    document_id = uploaded["id"]
    print("Uploaded:", json.dumps(uploaded, indent=2))

    resp = requests.post(
        f"{BASE_URL}/test-documents/{document_id}/process",
        timeout=300,
    )
    resp.raise_for_status()
    processed = resp.json()
    print("Processed:", json.dumps(processed, indent=2))

    resp = requests.post(
        f"{BASE_URL}/test-documents/{document_id}/run-extraction",
        json={
            "triggered_by": "local_smoke_test",
            "run_async": False,
            "force_recompute": True,
            "form_type": "filing_registration",
        },
        timeout=300,
    )
    resp.raise_for_status()
    extracted = resp.json()

    print("Extraction summary:")
    print(
        json.dumps(
            {
                "job": extracted.get("job"),
                "confirmed_count": extracted.get("confirmed_count"),
                "suggested_count": extracted.get("suggested_count"),
                "missing_count": extracted.get("missing_count"),
                "review_flags": extracted.get("review_flags"),
            },
            indent=2,
        )
    )

    print("\nGrouped:")
    print(json.dumps(extracted.get("grouped"), indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/smoke_test_local_pdf.py <path-to-pdf>")
    main(sys.argv[1])
