from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router

try:
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[2]
    backend_root = project_root / "backend"
    load_dotenv(project_root / ".env")
    load_dotenv(backend_root / ".env")
except Exception:
    pass


app = FastAPI(
    title="Filing Counter API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
