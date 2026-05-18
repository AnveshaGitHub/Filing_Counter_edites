from fastapi import APIRouter

from app.api.v1.filing_extraction import router as filing_extraction_router
from app.api.v1.filing_review import router as filing_review_router
from app.api.v1.filing_payload import router as filing_payload_router
from app.api.v1.test_documents import router as test_documents_router

api_router = APIRouter()
api_router.include_router(filing_extraction_router)
api_router.include_router(filing_review_router)
api_router.include_router(filing_payload_router)
api_router.include_router(test_documents_router)
